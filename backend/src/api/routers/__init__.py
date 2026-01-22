"""
API 路由分组模块
"""

from .wecom import wecom_router
from .craft import craft_router
from .news import news_router
from .telegram import telegram_router
from .lottery import router as lottery_router

__all__ = [
    "wecom_router",
    "craft_router",
    "news_router",
    "telegram_router",
    "lottery_router",
]