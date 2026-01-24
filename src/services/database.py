"""
数据库服务模块 (SQLite 版)
仅保留统一消息存储功能
"""
import json
import logging
import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

from src.models.chat_record import UnifiedMessage

logger = logging.getLogger(__name__)

# 数据库文件路径
_db_path = "data/craftsaver.db"


def init_db(db_path: str = None, **kwargs) -> None:
    """初始化数据库配置"""
    global _db_path
    if db_path:
        _db_path = db_path

    # 确保目录存在
    db_dir = os.path.dirname(_db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    logger.info(f"[DB] SQLite 数据库路径: {_db_path}")


@contextmanager
def get_connection():
    """获取数据库连接 (Context Manager)"""
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _parse_msg_time(ts) -> Optional[str]:
    """解析消息时间戳为 DATETIME 格式字符串"""
    if not ts:
        return None
    try:
        ts = int(ts)
        if ts > 1e11:
            ts = ts // 1000
        dt = datetime.fromtimestamp(ts)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError, OSError) as e:
        logger.warning(f"[DB] 时间戳解析失败: {ts}, error={e}")
        return None


class DatabaseService:
    """数据库服务类"""

    @staticmethod
    def get_connection():
        """获取原始数据库连接对象"""
        conn = sqlite3.connect(_db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def message_exists(msg: UnifiedMessage) -> bool:
        """检查统一消息是否已存在"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id FROM unified_messages WHERE source = ? AND msg_id = ?",
                    (msg.source, msg.msg_id)
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"[DB] 检查统一消息是否存在失败: msgid={msg.msg_id}, error={e}")
            return False

    @staticmethod
    def save_unified_message(msg: UnifiedMessage) -> bool:
        """保存统一消息"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()

                # 检查是否已存在
                cursor.execute(
                    "SELECT id FROM unified_messages WHERE source = ? AND msg_id = ?",
                    (msg.source, msg.msg_id)
                )
                if cursor.fetchone():
                    logger.info(f"[DB] 统一消息已存在，跳过: source={msg.source}, msgid={msg.msg_id}")
                    return False

                # 插入新消息
                sql = """
                INSERT INTO unified_messages
                (msg_id, source, msg_type, from_user, content, raw_data, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """

                created_at = _parse_msg_time(msg.create_time)

                cursor.execute(sql, (
                    msg.msg_id,
                    msg.source,
                    msg.msg_type,
                    msg.from_user,
                    msg.content,
                    json.dumps(msg.raw_data, ensure_ascii=False),
                    created_at
                ))
                conn.commit()
                logger.info(f"[DB] 统一消息保存成功: source={msg.source}, msgid={msg.msg_id}")
                return True

        except Exception as e:
            logger.error(f"[DB] 保存统一消息失败: msgid={msg.msg_id}, error={e}")
            return False

    @staticmethod
    def get_last_seq() -> int:
        """获取最后处理的序号"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(seq) FROM wecom_messages")
                result = cursor.fetchone()
                return result[0] if result and result[0] else 0
        except Exception as e:
            logger.warning(f"[DB] 获取最后序号失败: {e}")
            return 0
