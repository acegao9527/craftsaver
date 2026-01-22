import logging
from src.handlers.base import BaseHandler
from src.models.chat_record import UnifiedMessage

logger = logging.getLogger(__name__)

class TestHandler(BaseHandler):
    """
    处理测试指令
    Priority: 3
    """
    async def check(self, msg: UnifiedMessage) -> bool:
        if msg.msg_type == "text" and "测试" in msg.content:
            # 限制长度，避免误伤长句中包含“测试”
            return len(msg.content.strip()) <= 5
        return False

    async def handle(self, msg: UnifiedMessage):
        logger.info(f"[TestHandler] Processing test message: {msg.msg_id}")
        await self.reply(msg, "我是你的 Agent，欢迎测试我")
        # Explicitly DO NOT save to Craft
