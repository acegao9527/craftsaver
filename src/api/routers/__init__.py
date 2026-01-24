"""
API 路由分组模块
"""

from .wecom import wecom_router
from .craft import craft_router
from .binding import binding_router

__all__ = [
    "wecom_router",
    "craft_router",
    "binding_router",
]