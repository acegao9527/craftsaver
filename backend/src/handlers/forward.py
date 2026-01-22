"""
消息转发处理器 - 将企微消息转发到用户绑定的 Craft 文档
"""
import logging
from src.models.chat_record import UnifiedMessage
from src.handlers.base import BaseHandler
from src.services.binding_service import BindingService
from src.services.formatter import format_unified_message_as_craft_blocks
from src.services.craft import save_blocks_to_craft
from src.utils.reply_sender import send_reply

logger = logging.getLogger(__name__)


class ForwardHandler(BaseHandler):
    """消息转发处理器 - 将消息转发到绑定的 Craft 文档"""

    async def check(self, msg: UnifiedMessage) -> bool:
        """
        检查是否应该处理该消息
        条件：
        1. 来源是企微
        2. 消息类型是有效的转发类型（非命令）
        """
        if msg.source != "wecom":
            return False

        # 排除绑定相关命令（由 BindHandler 处理）
        if msg.msg_type == "text":
            content = msg.content.strip()
            if content.startswith("绑定") or content.startswith("我的绑定"):
                return False

        return True

    async def handle(self, msg: UnifiedMessage):
        """处理消息转发"""
        from_user = msg.from_user

        # 查询用户绑定配置
        binding = BindingService.get_binding_by_openid(from_user)

        if not binding:
            # 尝试使用默认用户
            default_target = BindingService.get_default_target()
            if not default_target:
                logger.warning(f"[Forward] 用户 {from_user} 未绑定，且未配置默认用户，跳过转发")
                return

            link_id = default_target["link_id"]
            document_id = default_target["document_id"]
            token = default_target.get("token")
            logger.info(f"[Forward] 用户 {from_user} 未绑定，使用默认文档")
        else:
            link_id = binding.craft_link_id
            document_id = binding.craft_document_id
            token = binding.craft_token
            logger.info(f"[Forward] 用户 {from_user} -> link={link_id}, doc={document_id}")

        # 格式化为 Craft blocks
        blocks = format_unified_message_as_craft_blocks(msg)

        if not blocks:
            logger.warning(f"[Forward] 消息格式化为空: msgid={msg.msg_id}")
            return

        # 发送到 Craft
        try:
            success = await save_blocks_to_craft(
                blocks,
                link_id=link_id,
                document_id=document_id,
                document_token=token
            )

            if success:
                logger.info(f"[Forward] 转发成功: msgid={msg.msg_id}")
            else:
                logger.error(f"[Forward] 转发失败: msgid={msg.msg_id}")
                # 可以选择发送失败通知
                await send_reply(msg, "⚠️ 转发到 Craft 失败，请稍后重试")
        except Exception as e:
            logger.error(f"[Forward] 转发异常: msgid={msg.msg_id}, error={e}")
            await send_reply(msg, f"⚠️ 转发异常: {str(e)}")
