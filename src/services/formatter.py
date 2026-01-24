"""
消息格式化服务模块

将企微消息格式化为 Craft blocks
"""
import os
import logging
from typing import List, Dict, Any, Optional

from src.models.chat_record import UnifiedMessage

logger = logging.getLogger(__name__)


def upload_to_cos(local_path: str) -> Optional[str]:
    """上传文件到 COS，返回公开访问 URL"""
    try:
        from src.services.cos import upload_image
        url = upload_image(local_path)
        if url:
            return url
        logger.error(f"[Formatter] COS 上传失败: {local_path}")
        return None
    except Exception as e:
        logger.error(f"[Formatter] COS 上传异常: {e}")
        return None


class MessageFormatter:
    """消息格式化服务"""

    def __init__(self):
        pass

    def format_unified(self, msg: UnifiedMessage) -> List[Dict[str, Any]]:
        """
        格式化 UnifiedMessage 为 Craft blocks
        """
        blocks = []

        # 内容处理
        if msg.msg_type == "text":
            blocks.append({
                "type": "text",
                "markdown": msg.content
            })
        elif msg.msg_type == "image":
            # 图片处理
            if msg.content:
                # 检查是否是有效的 URL（以 http:// 或 https:// 开头）
                if msg.content.startswith("http://") or msg.content.startswith("https://"):
                    blocks.append({
                        "type": "image",
                        "url": msg.content
                    })
                # 检查本地文件是否存在
                elif os.path.exists(msg.content):
                    # 上传到 COS 获取公开 URL
                    cos_url = upload_to_cos(msg.content)
                    if cos_url:
                        blocks.append({
                            "type": "image",
                            "url": cos_url
                        })
                    else:
                        filename = os.path.basename(msg.content)
                        logger.warning(f"[Formatter] 图片上传失败，使用文件名作为描述: {filename}")
                        blocks.append({
                            "type": "text",
                            "markdown": f"🖼 **{filename}**"
                        })
                else:
                    blocks.append({
                        "type": "text",
                        "markdown": f"🖼 **收到图片** (路径无效): `{msg.content}`"
                    })
            else:
                blocks.append({
                    "type": "text",
                    "markdown": "🖼 **收到图片** (无内容)"
                })
        elif msg.msg_type == "file":
            # 文件处理
            if msg.content:
                # 优先从原始数据中获取真实文件名
                raw_file_data = msg.raw_data.get("file", {}) if msg.raw_data else {}
                display_name = raw_file_data.get("filename")

                # 检查是否是有效的 URL
                if msg.content.startswith("http://") or msg.content.startswith("https://"):
                    if not display_name:
                        display_name = msg.content.split("/")[-1]
                    blocks.append({
                        "type": "file",
                        "url": msg.content,
                        "fileName": display_name,
                        "markdown": f"[{display_name}]({msg.content})"
                    })
                # 检查本地文件是否存在
                elif os.path.exists(msg.content):
                    if not display_name:
                        display_name = os.path.basename(msg.content)

                    # 上传到 COS
                    cos_url = upload_to_cos(msg.content)
                    if cos_url:
                        blocks.append({
                            "type": "file",
                            "url": cos_url,
                            "fileName": display_name,
                            "markdown": f"[{display_name}]({cos_url})"
                        })
                    else:
                        logger.warning(f"[Formatter] 文件上传失败: {display_name}")
                        blocks.append({
                            "type": "text",
                            "markdown": f"📁 **{display_name}** (上传失败)"
                        })
                else:
                    blocks.append({
                        "type": "text",
                        "markdown": f"📁 **收到文件** (路径无效): `{msg.content}`"
                    })
            else:
                blocks.append({
                    "type": "text",
                    "markdown": "📁 **收到文件** (无内容)"
                })
        elif msg.msg_type == "video":
            # 视频处理
            if msg.content:
                if msg.content.startswith("http://") or msg.content.startswith("https://"):
                    filename = msg.content.split("/")[-1]
                    blocks.append({
                        "type": "file",
                        "url": msg.content,
                        "fileName": filename,
                        "markdown": f"[{filename}]({msg.content})"
                    })
                elif os.path.exists(msg.content):
                    filename = os.path.basename(msg.content)
                    cos_url = upload_to_cos(msg.content)
                    if cos_url:
                        blocks.append({
                            "type": "file",
                            "url": cos_url,
                            "fileName": filename,
                            "markdown": f"[{filename}]({cos_url})"
                        })
                    else:
                        logger.warning(f"[Formatter] 视频上传失败: {filename}")
                        blocks.append({
                            "type": "text",
                            "markdown": f"🎥 **{filename}** (上传失败)"
                        })
                else:
                    blocks.append({
                        "type": "text",
                        "markdown": f"🎥 **收到视频** (路径无效): `{msg.content}`"
                    })
            else:
                blocks.append({
                    "type": "text",
                    "markdown": "🎥 **收到视频** (无内容)"
                })
        elif msg.msg_type == "link":
            final_url = msg.content.strip()

            if final_url and final_url.startswith("http"):
                blocks.append({
                    "type": "richUrl",
                    "url": final_url
                })
            else:
                blocks.append({
                    "type": "text",
                    "markdown": f"🔗 **无效链接**: {final_url}"
                })
        else:
            blocks.append({
                "type": "text",
                "markdown": f"[{msg.msg_type}] {msg.content}"
            })

        return blocks


# 全局格式化器实例
_formatter = None


def get_formatter() -> MessageFormatter:
    """获取消息格式化器实例"""
    global _formatter
    if _formatter is None:
        _formatter = MessageFormatter()
    return _formatter


def format_unified_message_as_craft_blocks(msg: UnifiedMessage) -> List[Dict[str, Any]]:
    """将 UnifiedMessage 格式化为 Craft blocks"""
    return get_formatter().format_unified(msg)
