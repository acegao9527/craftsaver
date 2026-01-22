"""
API 路由分组模块
"""

from .wecom import wecom_router
from .craft import craft_router

__all__ = [
    "wecom_router",
    "craft_router",
]