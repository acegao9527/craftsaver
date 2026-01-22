"""
iMessage 数据模型定义
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Any
from enum import Enum


class MessageType(Enum):
    """消息类型"""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    FILE = "file"
    LOCATION = "location"
    CONTACT = "contact"
    UNKNOWN = "unknown"


class MessageDirection(Enum):
    """消息方向"""
    INCOMING = "incoming"
    OUTGOING = "outgoing"


@dataclass
class Message:
    """iMessage 消息模型"""
    id: int
    guid: str
    text: str
    sender: str  # 电话号码或邮箱
    receiver: str
    timestamp: datetime
    direction: MessageDirection
    message_type: MessageType = MessageType.TEXT
    is_read: bool = False
    is_delivered: bool = False
    is_played: bool = False
    attachments: List[str] = field(default_factory=list)

    @classmethod
    def from_row(cls, row: Any) -> "Message":
        """从数据库行转换"""
        # sqlite3.Row 支持 key 访问和索引访问
        try:
            msg_id = row["ROWID"]
            guid = row["guid"] if "guid" in row.keys() else ""
            text = row["text"] if "text" in row.keys() else ""
            handle_id = row["handle_id"] if "handle_id" in row.keys() else 0
            msg_type = row["type"] if "type" in row.keys() else 0
            timestamp = cls._mac_timestamp_to_datetime(row["date"] if "date" in row.keys() else None)
            is_from_me = row["is_from_me"] if "is_from_me" in row.keys() else 0
        except (KeyError, TypeError, IndexError):
            # Fallback to index access
            row = tuple(row)
            msg_id = row[0] if len(row) > 0 else 0
            guid = row[1] if len(row) > 1 else ""
            text = row[2] if len(row) > 2 else ""
            handle_id = row[3] if len(row) > 3 else 0
            msg_type = row[5] if len(row) > 5 else 0
            timestamp = cls._mac_timestamp_to_datetime(row[6] if len(row) > 6 else None)
            is_from_me = row[17] if len(row) > 17 else 0  # is_from_me is at index 17 in our query

        # 获取消息类型
        if msg_type == 0:
            message_type = MessageType.TEXT
        elif msg_type == 2:
            message_type = MessageType.IMAGE
        elif msg_type == 3:
            message_type = MessageType.VIDEO
        elif msg_type == 4:
            message_type = MessageType.FILE
        else:
            message_type = MessageType.UNKNOWN

        direction = MessageDirection.OUTGOING if is_from_me else MessageDirection.INCOMING

        return cls(
            id=msg_id,
            guid=guid,
            text=text,
            sender="",
            receiver="",
            timestamp=timestamp,
            direction=direction,
            message_type=message_type,
        )

    @staticmethod
    def _mac_timestamp_to_datetime(mac_timestamp: int) -> datetime:
        """将 macOS 时间戳转换为 Python datetime"""
        if mac_timestamp is None:
            return datetime.now()
        try:
            # macOS 时间戳从 2001-01-01 00:00:00 UTC 开始
            # 注意：iMessage 数据库中的 date 字段是纳秒格式（18位数字）
            timestamp_val = float(mac_timestamp)
            if timestamp_val > 10**16:  # 纳秒格式
                timestamp_val = timestamp_val / 10**9
            from datetime import timedelta
            epoch = datetime(2001, 1, 1, tzinfo=None)
            return epoch + timedelta(seconds=timestamp_val)
        except (ValueError, TypeError, OverflowError):
            return datetime.now()


@dataclass
class Chat:
    """iMessage 对话模型"""
    id: int
    guid: str
    display_name: str
    participants: List[str]
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None
    unread_count: int = 0

    @classmethod
    def from_row(cls, row: Any) -> "Chat":
        """从数据库行转换"""
        
        # 使用字典风格访问，提高健壮性
        # 注意：sqlite3.Row 支持 key 访问
        
        try:
            msg_id = row["ROWID"]
            guid = row["guid"]
            text = row["text"]
            # msg_service = row["service"] # 暂时不用
        except (IndexError, KeyError):
            # Fallback for simpler testing or missing columns
            msg_id = row[0] if len(row) > 0 else 0
            guid = row[1] if len(row) > 1 else ""
            text = row[2] if len(row) > 2 else ""

        # 获取消息类型
        try:
            msg_type_val = row["type"]
        except (IndexError, KeyError):
             msg_type_val = row[5] if len(row) > 5 else 0

        if msg_type_val == 0:
            message_type = MessageType.TEXT
        elif msg_type_val == 2:
            message_type = MessageType.IMAGE
        elif msg_type_val == 3:
            message_type = MessageType.VIDEO
        elif msg_type_val == 4:
            message_type = MessageType.FILE
        else:
            message_type = MessageType.UNKNOWN

        # 时间戳转换
        try:
           date_val = row["date"]
        except (IndexError, KeyError):
           date_val = row[6] if len(row) > 6 else None
        
        timestamp = cls._mac_timestamp_to_datetime(date_val)

        # 判断方向
        try:
            is_from_me_val = row["is_from_me"]
        except (IndexError, KeyError):
            # Fallback (old logic was row[24] from handle which is risky)
            is_from_me_val = 0 
        
        direction = MessageDirection.OUTGOING if is_from_me_val else MessageDirection.INCOMING

        return cls(
            id=msg_id,
            guid=guid,
            text=text,
            sender="",
            receiver="",
            timestamp=timestamp,
            direction=direction,
            message_type=message_type,
        )

    @staticmethod
    def _mac_timestamp_to_datetime(mac_timestamp: int) -> datetime:
        """将 macOS 时间戳转换为 Python datetime"""
        if mac_timestamp is None:
            return datetime.now()
        try:
            # macOS 时间戳从 2001-01-01 00:00:00 UTC 开始
            # 注意：数据库中存储的是 nano seconds 还是 seconds?
            # 实际上 macOS iMessage date 是从 2001-01-01 开始的 *秒数* (float/int)
            # 有时它是纳秒 (18位)，有时是秒 (9位)。
            # 通常 chat.db 里是纳秒 (Nanoseconds since 2001-01-01 00:00:00)
            
            timestamp_val = float(mac_timestamp)
            
            # 简单的启发式判断：如果数字非常大（例如 > 10^17），可能是纳秒
            if timestamp_val > 10**16:
                timestamp_val = timestamp_val / 10**9
                
            from datetime import timedelta
            epoch = datetime(2001, 1, 1, tzinfo=None)
            return epoch + timedelta(seconds=timestamp_val)
        except (ValueError, TypeError, OverflowError):
            return datetime.now()


@dataclass
class Chat:
    """iMessage 对话模型"""
    id: int
    guid: str
    display_name: str
    participants: List[str]
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None
    unread_count: int = 0

    @classmethod
    def from_row(cls, row: Any) -> "Chat":
        """从数据库行转换"""
        try:
            chat_id = row["ROWID"]
            guid = row["guid"]
            display_name = row["display_name"]
        except (IndexError, KeyError):
            chat_id = row[0] if len(row) > 0 else 0
            guid = row[1] if len(row) > 1 else ""
            display_name = row[3] if len(row) > 3 else ""

        participants = []
        last_message = None
        last_message_time = None
        unread_count = 0

        return cls(
            id=chat_id,
            guid=guid,
            display_name=display_name,
            participants=participants,
            last_message=last_message,
            last_message_time=last_message_time,
            unread_count=unread_count,
        )
