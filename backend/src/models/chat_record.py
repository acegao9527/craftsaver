from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Union

class UnifiedMessage(BaseModel):
    """
    统一消息模型
    """
    msg_id: str = Field(..., description="原始平台的消息ID")
    source: str = Field(..., description="消息来源: wecom")
    msg_type: str = Field(..., description="消息类型: text, image, link, voice, video, file")
    content: str = Field(..., description="文本内容 或 媒体文件的本地绝对路径")
    from_user: str = Field(..., description="发送者用户名或ID")
    create_time: int = Field(..., description="消息创建时间戳(秒)")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="原始数据备份")

    class Config:
        extra = "ignore"
