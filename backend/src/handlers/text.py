import logging
from src.handlers.base import BaseHandler
from src.models.chat_record import UnifiedMessage
from src.services.craft import save_blocks_to_craft
from src.services.formatter import format_unified_message_as_craft_blocks

logger = logging.getLogger(__name__)

class DefaultHandler(BaseHandler):
    """
    处理其他所有消息
    Priority: Lowest
    """
    async def check(self, msg: UnifiedMessage) -> bool:
        # 永远返回 True，作为兜底
        return True

    async def handle(self, msg: UnifiedMessage):
        logger.info(f"[DefaultHandler] Processing generic message: {msg.msg_id}")
        
        # 1. 保存到 Craft
        blocks = format_unified_message_as_craft_blocks(msg)
        if not blocks:
            logger.warning(f"[DefaultHandler] Formatter returned empty blocks: {msg.msg_id}")
            return

        success = await save_blocks_to_craft(blocks)
        
        # 2. 回复 (仅成功时)
        if success:
            await self.reply(msg, "✅ 消息已同步到 Craft")
        else:
            # 失败通常不打扰用户，或者打 error log
            logger.error(f"[DefaultHandler] Save failed for {msg.msg_id}")