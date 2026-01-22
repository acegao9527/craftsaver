from abc import ABC, abstractmethod
import logging
from src.models.chat_record import UnifiedMessage
from src.utils.reply_sender import send_reply

logger = logging.getLogger(__name__)

class BaseHandler(ABC):
    """
    消息处理器基类
    """
    
    @abstractmethod
    async def check(self, msg: UnifiedMessage) -> bool:
        """检查是否应该处理该消息"""
        pass

    @abstractmethod
    async def handle(self, msg: UnifiedMessage):
        """执行处理逻辑"""
        pass
        
    async def reply(self, msg: UnifiedMessage, text: str):
        """发送回复的便捷方法"""
        await send_reply(msg, text)