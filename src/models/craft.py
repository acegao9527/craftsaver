"""
Craft 相关数据模型
"""
from pydantic import BaseModel


class CraftMessage(BaseModel):
    """Craft 消息模型"""
    message: str
