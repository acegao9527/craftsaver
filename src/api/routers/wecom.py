"""
企业微信回调路由
"""
import logging
import time
import xml.etree.cElementTree as ET

from fastapi import APIRouter, Request, Response

from src.services.wecom import WeComService, download_image

logger = logging.getLogger(__name__)

wecom_router = APIRouter(prefix="/wecom", tags=["WeCom"])


from src.models.chat_record import UnifiedMessage
from src.services.message_processor import process_message

async def _process_wecom_messages() -> dict:
    """
    处理企微消息：获取消息 -> 转换为统一模型 -> 统一处理 (落库+同步)

    Returns:
        处理结果统计
    """
    from src.services.database import DatabaseService

    start_seq = DatabaseService.get_last_seq()
    messages = WeComService.fetch_messages()
    logger.info(f"[WeCom] 获取到 {len(messages)} 条消息, 起始 seq={start_seq}")

    processed_count = 0
    
    for i, msg in enumerate(messages):
        try:
            msg_id = msg.get('msgid')
            msg_type = msg.get('msgtype')
            from_user = msg.get('from')
            msg_time = msg.get('msgtime', 0) / 1000 # 毫秒转秒
            
            logger.info(f"[WeCom] 处理消息 {i+1}/{len(messages)}: msgid={msg_id}, type={msg_type}")
            
            content = ""
            
            # 提取内容
            if msg_type == "text":
                content = msg.get("text", {}).get("content", "")
                
                # Check if text is a URL
                import re
                url_pattern = re.compile(r'^(https?://[^\s]+)$', re.IGNORECASE)
                if url_pattern.match(content.strip()):
                     msg_type = "link"
                     # Keep content as is (the URL)
            elif msg_type == "image":
                # 图片消息，下载图片
                image_data = msg.get("image", {})
                sdk_file_id = image_data.get("sdkfileid")
                if sdk_file_id:
                    local_path = download_image(sdk_file_id, msg_id, file_extension="jpg")
                    content = local_path if local_path else "[图片下载失败]"
                else:
                    content = "[图片无SDKFileID]"
            elif msg_type == "file":
                # 文件消息，下载文件
                file_data = msg.get("file", {})
                sdk_file_id = file_data.get("sdkfileid")
                file_ext = file_data.get("fileext", "bin")
                original_filename = file_data.get("filename", "")
                
                # 检查是否为视频文件
                if file_ext.lower() in ["mp4", "mov", "avi", "mkv", "webm"]:
                    msg_type = "video"
                    # 下载逻辑与 file 相同，但标记为 video
                    if sdk_file_id:
                        local_path = download_image(sdk_file_id, msg_id, file_extension=file_ext, original_name=original_filename)
                        content = local_path if local_path else "[视频下载失败]"
                    else:
                        content = "[视频无SDKFileID]"
                else:
                    if sdk_file_id:
                        local_path = download_image(sdk_file_id, msg_id, file_extension=file_ext, original_name=original_filename)
                        content = local_path if local_path else "[文件下载失败]"
                    else:
                        content = "[文件无SDKFileID]"
            elif msg_type == "video":
                # 视频消息，下载视频
                video_data = msg.get("video", {})
                sdk_file_id = video_data.get("sdkfileid")
                if sdk_file_id:
                    # 视频通常为 mp4
                    local_path = download_image(sdk_file_id, msg_id, file_extension="mp4")
                    content = local_path if local_path else "[视频下载失败]"
                else:
                    content = "[视频无SDKFileID]"
            elif msg_type == "link":
                link_data = msg.get("link", {})
                logger.info(f"[WeCom] Link Data: {link_data}") # Debug log
                title = link_data.get("title", "无标题")
                url = link_data.get("link_url") or link_data.get("url", "")
                content = url # 直接存储 URL，不再使用 Markdown 格式
            else:
                # 其他类型暂存原始JSON字符串或简要描述
                content = f"[{msg_type}]"

            # 构建统一消息对象
            unified_msg = UnifiedMessage(
                msg_id=msg_id,
                source="wecom",
                msg_type=msg_type,
                content=content,
                from_user=from_user,
                create_time=int(msg_time),
                raw_data=msg
            )
            
            # 统一处理
            await process_message(unified_msg)
            processed_count += 1
            
        except Exception as e:
            logger.error(f"[WeCom] 消息转换/处理失败: {msg.get('msgid')}, error={e}")

    logger.info(f"[WeCom] 处理完成: 总数={len(messages)}, 成功处理={processed_count}")

    return {
        "seq": start_seq,
        "total": len(messages),
        "processed": processed_count
    }


@wecom_router.post("/callback")
async def wecom_receive_message(request: Request):
    """
    企业微信回调接口
    """
    try:
        body = await request.body()
        if not body:
            logger.info("[WeCom] 收到空回调请求体，执行主动拉取")
        else:
            xml_str = body.decode('utf-8')
            logger.info(f"[WeCom] 收到回调 XML: {xml_str[:200]}...")

            msg_type = ""
            media_id = ""
            from_user = ""
            msg_time = ""

            try:
                root = ET.fromstring(xml_str)
                msg_type_elem = root.find('MsgType')
                msg_type = msg_type_elem.text if msg_type_elem is not None and msg_type_elem.text else ""

                from_user_elem = root.find('FromUserName')
                from_user = from_user_elem.text if from_user_elem is not None and from_user_elem.text else ""

                create_time_elem = root.find('CreateTime')
                msg_time = create_time_elem.text if create_time_elem is not None and create_time_elem.text else ""

                # 提取 MediaId
                media_id_elem = root.find('MediaId')
                media_id = media_id_elem.text if media_id_elem is not None and media_id_elem.text else ""

                logger.info(f"[WeCom] 回调消息类型: {msg_type}, from={from_user}, media_id={media_id[:20] if media_id else 'None'}...")

                # 如果是图片消息，直接处理
                if msg_type == "image" and media_id:
                    logger.info(f"[WeCom] 直接处理图片消息: media_id={media_id}")
                    local_path = download_image(media_id, f"callback_{int(time.time())}")
                    if local_path:
                        logger.info(f"[WeCom] 图片下载成功: {local_path}")
                    else:
                        logger.warning(f"[WeCom] 图片下载失败")

            except ET.ParseError as e:
                logger.warning(f"[WeCom] XML 解析失败: {e}")

        result = await _process_wecom_messages()
        return {"status": "success", **result}

    except Exception as e:
        logger.error(f"[WeCom] 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}
