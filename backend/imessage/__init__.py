"""
iMessage Module - macOS iMessage 收发模块

仅在 macOS 环境下使用，通过 AppleScript 发送消息，SQLite 读取消息历史。
"""

import sys
import platform

if platform.system() != "Darwin":
    raise ImportError("iMessage 模块仅支持 macOS 系统")

from .client import iMessageClient
from .models import Message, Chat

__all__ = ["iMessageClient", "Message", "Chat"]
