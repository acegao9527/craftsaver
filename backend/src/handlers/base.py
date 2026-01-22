from abc import ABC, abstractmethod
import logging
from src.models.chat_record import UnifiedMessage

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