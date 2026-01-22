
"""
数据库服务模块 (SQLite 版)
"""
import json
import logging
import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List, Tuple

from src.models.chat_record import UnifiedMessage
from src.models.email import Email, EmailSummary

logger = logging.getLogger(__name__)

# 数据库文件路径
_db_path = "data/savehelper.db"


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
    conn.row_factory = sqlite3.Row  # 允许通过列名访问
    try:
        yield conn
    finally:
        conn.close()


def _parse_msg_time(ts) -> Optional[str]:
    """
    解析消息时间戳为 DATETIME 格式字符串
    """
    if not ts:
        return None
    try:
        ts = int(ts)
        # 如果是毫秒级时间戳（13位），转换为秒
        if ts > 1e11:
            ts = ts // 1000
        dt = datetime.fromtimestamp(ts)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError, OSError) as e:
        logger.warning(f"[DB] 时间戳解析失败: {ts}, error={e}")
        return None


class DatabaseService:
    """数据库服务类"""

    def __init__(self):
        pass

    @staticmethod
    def get_connection():
        """获取原始数据库连接对象 (Callers must close it manually)"""
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
    def save_message(msg: dict) -> bool:
        """保存企微消息"""
        msgid = msg.get("msgid")
        if not msgid:
            logger.warning("[DB] 消息缺少 msgid，跳过保存")
            return False

        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                # 检查是否已存在
                cursor.execute("SELECT id FROM wecom_messages WHERE msgid = ?", (msgid,))
                if cursor.fetchone():
                    logger.info(f"[DB] 消息已存在，跳过: msgid={msgid}")
                    return False

                # 插入新消息
                sql = """
                INSERT INTO wecom_messages
                (msgid, seq, chat_type, room_name, msgtype, from_user, tolist, content, action, msg_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                tolist = json.dumps(msg.get("tolist", []), ensure_ascii=False)
                msg_time = _parse_msg_time(msg.get("msgtime") or msg.get("msg_time"))

                # 获取消息内容 (逻辑同前)
                msg_type = msg.get("msgtype", "")
                content = ""
                
                media_types = ["image", "voice", "video", "file", "link", "location", "emotion"]
                if msg_type in media_types and msg.get(msg_type):
                    media_obj = msg.get(msg_type)
                    if isinstance(media_obj, (dict, list)):
                        content = json.dumps(media_obj, ensure_ascii=False)
                
                if not content:
                    content_raw = msg.get("content")
                    if isinstance(content_raw, (dict, list)):
                        content = json.dumps(content_raw, ensure_ascii=False)
                    elif isinstance(content_raw, str):
                        content = content_raw
                    elif content_raw is not None:
                        content = str(content_raw)
                    
                    if not content:
                        text_raw = msg.get("text") or msg.get("msg")
                        if isinstance(text_raw, (dict, list)):
                            content = json.dumps(text_raw, ensure_ascii=False)
                        elif isinstance(text_raw, str):
                            content = text_raw
                        elif text_raw is not None:
                            content = str(text_raw)

                chat_type = msg.get("chat_type") or msg.get("chattype") or msg.get("chatType")
                room_name = msg.get("room_name") or msg.get("roomname") or msg.get("roomName") or msg.get("group_name")

                cursor.execute(sql, (
                    msgid,
                    msg.get("seq", 0),
                    chat_type,
                    room_name,
                    msg.get("msgtype"),
                    msg.get("from"),
                    tolist,
                    content,
                    msg.get("action"),
                    msg_time,
                ))
                conn.commit()

                logger.info(f"[DB] 消息保存成功: msgid={msgid}")
                return True

        except Exception as e:
            logger.error(f"[DB] 保存消息失败: msgid={msgid}, error={e}")
            return False

    @staticmethod
    def save_messages_batch(messages: List[dict]) -> Tuple[int, int]:
        """批量保存"""
        inserted = 0
        skipped = 0
        for msg in messages:
            if DatabaseService.save_message(msg):
                inserted += 1
            else:
                skipped += 1
        logger.info(f"[DB] 批量保存完成: 插入={inserted}, 跳过={skipped}")
        return inserted, skipped

    @staticmethod
    def get_message_by_msgid(msgid: str) -> Optional[dict]:
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM wecom_messages WHERE msgid = ?", (msgid,))
                # sqlite3.Row 转换为 dict
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"[DB] 查询消息失败: msgid={msgid}, error={e}")
            return None

    @staticmethod
    def get_messages_by_user(user: str, limit: int = 100) -> list:
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM wecom_messages WHERE from_user = ? ORDER BY msg_time DESC LIMIT ?",
                    (user, limit),
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"[DB] 查询用户消息失败: user={user}, error={e}")
            return []


# 便捷函数
def save_wecom_message(msg: dict) -> bool:
    return DatabaseService.save_message(msg)

def save_wecom_messages_batch(messages: list) -> Tuple[int, int]:
    return DatabaseService.save_messages_batch(messages)


class EmailDatabaseService:
    """邮件数据库服务"""

    @staticmethod
    def email_exists(email_account: str, uid: str) -> bool:
        """检查邮件是否已存在"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id FROM emails WHERE email_account = ? AND uid = ?",
                    (email_account, uid)
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"[DB] 检查邮件是否存在失败: account={email_account}, uid={uid}, error={e}")
            return False

    @staticmethod
    def save_email(email: Email, summary: EmailSummary = None) -> bool:
        """保存邮件"""
        try:
            if EmailDatabaseService.email_exists(email.email_account, email.uid):
                logger.info(f"[DB] 邮件已存在，跳过: account={email.email_account}, uid={email.uid}")
                return False

            with get_connection() as conn:
                cursor = conn.cursor()
                sql = """
                INSERT INTO emails
                (email_account, uid, subject, sender, sender_name, received_at, preview, summary, importance, action_items, raw_content, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                action_items_json = json.dumps(summary.action_items) if summary else "[]"

                cursor.execute(sql, (
                    email.email_account,
                    email.uid,
                    email.subject,
                    email.sender,
                    email.sender_name,
                    email.received_at,
                    email.preview,
                    summary.summary if summary else None,
                    summary.importance if summary else "medium",
                    action_items_json,
                    email.raw_content,
                    email.created_at or int(datetime.now().timestamp())
                ))
                conn.commit()
                logger.info(f"[DB] 邮件保存成功: account={email.email_account}, uid={email.uid}")
                return True

        except Exception as e:
            logger.error(f"[DB] 保存邮件失败: account={email.email_account}, uid={email.uid}, error={e}")
            return False

    @staticmethod
    def get_email_by_uid(email_account: str, uid: str) -> Optional[dict]:
        """根据 UID 查询邮件"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM emails WHERE email_account = ? AND uid = ?",
                    (email_account, uid)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"[DB] 查询邮件失败: account={email_account}, uid={uid}, error={e}")
            return None

    @staticmethod
    def get_recent_emails(email_account: str = None, limit: int = 50) -> list:
        """获取最近邮件"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                if email_account:
                    cursor.execute(
                        "SELECT * FROM emails WHERE email_account = ? ORDER BY received_at DESC LIMIT ?",
                        (email_account, limit)
                    )
                else:
                    cursor.execute(
                        "SELECT * FROM emails ORDER BY received_at DESC LIMIT ?",
                        (limit,)
                    )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"[DB] 查询最近邮件失败: error={e}")
            return []


# 便捷函数
def save_email(email: Email, summary: EmailSummary = None) -> bool:
    return EmailDatabaseService.save_email(email, summary)

