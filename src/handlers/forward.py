"""
消息转发处理器 - 将企微消息转发到用户绑定的 Craft 文档
"""
import logging
from src.models.chat_record import UnifiedMessage
from src.handlers.base import BaseHandler
from src.services.binding_service import BindingService, BindingCreate
from src.services.formatter import format_unified_message_as_craft_blocks
from src.services.craft import save_blocks_to_craft

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

        return True

    async def handle(self, msg: UnifiedMessage):
        """处理消息转发"""
        from_user = msg.from_user
        content = msg.content or ""

        # 检查是否是绑定命令：绑定 tokenId linkId docId
        if content.startswith("绑定"):
            parts = content.split()
            if len(parts) >= 4 and parts[0] == "绑定":
                token_id = parts[1]
                link_id = parts[2]
                doc_id = parts[3]

                # 创建绑定
                create = BindingCreate(
                    wecom_openid=from_user,
                    craft_link_id=link_id,
                    craft_document_id=doc_id,
                    craft_token=token_id,
                    display_name=None
                )
                binding = BindingService.create_binding(create)
                if binding:
                    logger.info(f"[Forward] 用户 {from_user} 绑定成功: link={link_id}, doc={doc_id}")
                else:
                    logger.error(f"[Forward] 用户 {from_user} 绑定失败")
                return

        # 查询用户绑定配置
        binding = BindingService.get_binding_by_openid(from_user)

        if not binding:
            logger.warning(f"[Forward] 用户 {from_user} 未绑定，跳过转发")
            return

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
        except Exception as e:
            logger.error(f"[Forward] 转发异常: msgid={msg.msg_id}, error={e}")
