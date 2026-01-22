"""
业务服务模块
"""

from .database import DatabaseService, init_db, save_wecom_message, save_wecom_messages_batch
from .wecom import WeComService, init_wecom, fetch_messages
from .craft import init_craft, save_blocks_to_craft
from .formatter import (
    MessageFormatter,
    format_unified_message_as_craft_blocks,
)
from .wecom_crypto import WXBizMsgCrypt
from . import ierror

__all__ = [
    "DatabaseService",
    "init_db",
    "save_wecom_message",
    "save_wecom_messages_batch",
    "WeComService",
    "init_wecom",
    "fetch_messages",
    "init_craft",
    "save_blocks_to_craft",
    "MessageFormatter",
    "format_unified_message_as_craft_blocks",
    "WXBizMsgCrypt",
    "ierror",
]
