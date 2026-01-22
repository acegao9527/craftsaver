"""
iMessage 客户端核心实现

通过 AppleScript 发送消息，SQLite 读取消息历史。
"""

import asyncio
import subprocess
import sqlite3
import os
import sys
import time
import logging
from pathlib import Path
from typing import Optional, List, Callable, Dict, Any
from datetime import datetime, timedelta
from pathlib import PurePath

# 支持直接运行和作为模块导入
try:
    from .models import Message, Chat, MessageType, MessageDirection
except ImportError:
    from models import Message, Chat, MessageType, MessageDirection

logger = logging.getLogger(__name__)


class iMessageClient:
    """iMessage 客户端"""

    def __init__(self):
        self.db_path = str(Path.home() / "Library" / "Messages" / "chat.db")
        self._last_checked_id: int = 0
        self._running: bool = False
        self._watch_task: Optional[asyncio.Task] = None
        self._watch_callbacks: List[Callable[[Message], None]] = []

    def _ensure_db_access(self) -> bool:
        """确保可以访问消息数据库"""
        if not os.path.exists(self.db_path):
            logger.error(f"消息数据库不存在: {self.db_path}")
            return False
        return True

    def _execute_applescript(self, script: str) -> tuple:
        """执行 AppleScript 并返回结果"""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", "Script execution timed out"
        except Exception as e:
            return -1, "", str(e)

    def send_text(self, recipient: str, message: str) -> bool:
        """
        发送文本消息

        Args:
            recipient: 收件人电话号码或邮箱
            message: 消息内容

        Returns:
            是否发送成功
        """
        # 处理特殊字符转义
        escaped_message = message.replace('"', '\\"').replace('\n', '\\n')

        script = f'''
        tell application "Messages"
            send "{escaped_message}" to buddy "{recipient}"
        end tell
        '''

        code, stdout, stderr = self._execute_applescript(script)

        if code == 0:
            logger.info(f"消息已发送至 {recipient}: {message[:50]}...")
            return True
        else:
            logger.error(f"发送消息失败: {stderr}")
            return False

    async def send_text_async(self, recipient: str, message: str) -> bool:
        """异步发送文本消息"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.send_text, recipient, message)

    def send_attachment(self, recipient: str, file_path: str) -> bool:
        """
        发送附件（图片、文件等）

        Args:
            recipient: 收件人电话号码或邮箱
            file_path: 附件文件路径

        Returns:
            是否发送成功
        """
        if not os.path.exists(file_path):
            logger.error(f"附件文件不存在: {file_path}")
            return False

        # 转换路径为 macOS 路径格式
        abs_path = os.path.abspath(file_path)
        escaped_path = abs_path.replace('"', '\\"')

        script = f'''
        tell application "Messages"
            send "{escaped_path}" to buddy "{recipient}"
        end tell
        '''

        code, stdout, stderr = self._execute_applescript(script)

        if code == 0:
            logger.info(f"附件已发送至 {recipient}: {abs_path}")
            return True
        else:
            logger.error(f"发送附件失败: {stderr}")
            return False

    async def send_attachment_async(self, recipient: str, file_path: str) -> bool:
        """异步发送附件"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.send_attachment, recipient, file_path)

    def _get_connection(self) -> Optional[sqlite3.Connection]:
        """获取数据库连接"""
        if not self._ensure_db_access():
            return None

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"连接数据库失败: {e}")
            return None

    def _parse_handle_id(self, handle_id: int) -> str:
        """从 handle_id 获取联系人信息（返回原始手机号，不带国家代码前缀）"""
        try:
            conn = self._get_connection()
            if not conn:
                return ""

            cursor = conn.cursor()
            cursor.execute("SELECT id, country FROM handle WHERE ROWID = ?", (handle_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                phone = row["id"] or ""
                # 返回原始手机号，不添加国家代码前缀
                return phone
            return ""
        except Exception as e:
            logger.error(f"查询 handle 失败: {e}")
            return ""

    def _get_message_with_sender(self, row: sqlite3.Row) -> Message:
        """从数据库行获取完整的消息对象"""
        msg = Message.from_row(row)

        # 获取发送者/接收者信息
        handle_id = row["handle_id"] if "handle_id" in row.keys() else None
        if handle_id:
            contact = self._parse_handle_id(handle_id)
            if msg.direction == MessageDirection.OUTGOING:
                msg.receiver = contact
            else:
                msg.sender = contact

        return msg

    def get_messages(self, limit: int = 100, since_id: int = 0) -> List[Message]:
        """
        获取消息历史

        Args:
            limit: 最大返回消息数
            since_id: 仅获取大于此 ID 的消息

        Returns:
            消息列表
        """
        conn = self._get_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor()

            query = """
                SELECT m.ROWID, m.guid, m.text, m.handle_id, m.service,
                       m.type, m.date, m.date_delivered, m.date_read,
                       m.is_delivered, m.is_read, m.is_played,
                       m.group_title, m.group_action_type, m.share_status,
                       m.share_direction, m.message_summary_info,
                       m.is_from_me as is_from_me,
                       h.ROWID as handle_rowid, h.id as handle_address, h.country, h.service as handle_service,
                       h.uncanonicalized_id
                FROM message m
                LEFT JOIN handle h ON m.handle_id = h.ROWID
                WHERE m.ROWID > ?
                ORDER BY m.ROWID DESC
                LIMIT ?
            """

            cursor.execute(query, (since_id, limit))
            rows = cursor.fetchall()

            messages = []
            for row in rows:
                msg = self._get_message_with_sender(row)
                
                # Robust fix for direction
                try:
                     is_from_me_val = row["is_from_me"]
                     msg.direction = MessageDirection.OUTGOING if is_from_me_val else MessageDirection.INCOMING
                except:
                     pass

                messages.append(msg)

            conn.close()
            return messages[::-1]  # 按时间正序返回
        except Exception as e:
            logger.error(f"获取消息失败: {e}")
            conn.close()
            return []

    def get_chats(self, limit: int = 50) -> List[Chat]:
        """
        获取对话列表

        Args:
            limit: 最大返回对话数

        Returns:
            对话列表
        """
        conn = self._get_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor()

            query = """
                SELECT c.ROWID, c.guid, c.style, c.display_name, c.group_id,
                       c.accounts, c.cloud_id, c.machine_id
                FROM chat c
                ORDER BY c.ROWID DESC
                LIMIT ?
            """

            cursor.execute(query, (limit,))
            rows = cursor.fetchall()

            chats = []
            for row in rows:
                chat = Chat.from_row(row)
                chats.append(chat)

            conn.close()
            return chats
        except Exception as e:
            logger.error(f"获取对话失败: {e}")
            conn.close()
            return []

    def get_latest_message_id(self) -> int:
        """获取最新消息的 ID"""
        conn = self._get_connection()
        if not conn:
            return 0

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(ROWID) FROM message")
            result = cursor.fetchone()[0]
            conn.close()
            return result or 0
        except Exception as e:
            logger.error(f"获取最新消息 ID 失败: {e}")
            conn.close()
            return 0

    def watch_messages(
        self,
        callback: Callable[[Message], None],
        interval: float = 2.0,
        auto_reconnect: bool = True
    ) -> None:
        """
        监控新消息（同步版本）

        Args:
            callback: 新消息回调函数
            interval: 检查间隔（秒）
            auto_reconnect: 是否自动重连
        """
        self._watch_callbacks.append(callback)
        logger.info(f"开始监控新消息，检查间隔: {interval}秒")

        while self._running:
            try:
                if not self._ensure_db_access():
                    if not auto_reconnect:
                        break
                    time.sleep(interval)
                    continue

                messages = self.get_messages(since_id=self._last_checked_id)

                for msg in messages:
                    for cb in self._watch_callbacks:
                        try:
                            cb(msg)
                        except Exception as e:
                            logger.error(f"回调执行失败: {e}")

                    self._last_checked_id = msg.id

                time.sleep(interval)

            except Exception as e:
                logger.error(f"监控消息失败: {e}")
                if not auto_reconnect:
                    break
                time.sleep(interval)

    async def start_watching(
        self,
        callback: Callable[[Message], None],
        interval: float = 2.0,
        auto_reconnect: bool = True
    ) -> None:
        """
        开始监控新消息（异步版本）

        Args:
            callback: 新消息回调函数
            interval: 检查间隔（秒）
            auto_reconnect: 是否自动重连
        """
        self._running = True
        self._watch_callbacks.append(callback)

        self._watch_task = asyncio.create_task(
            self._watch_loop(callback, interval, auto_reconnect)
        )
        logger.info(f"异步监控已启动，检查间隔: {interval}秒")

    async def _watch_loop(
        self,
        callback: Callable[[Message], None],
        interval: float,
        auto_reconnect: bool
    ) -> None:
        """监控循环"""
        while self._running:
            try:
                if not self._ensure_db_access():
                    if not auto_reconnect:
                        break
                    await asyncio.sleep(interval)
                    continue

                messages = self.get_messages(since_id=self._last_checked_id)

                for msg in messages:
                    try:
                        await callback(msg)
                    except Exception as e:
                        logger.error(f"回调执行失败: {e}")

                    self._last_checked_id = msg.id

                await asyncio.sleep(interval)

            except Exception as e:
                logger.error(f"异步监控失败: {e}")
                if not auto_reconnect:
                    break
                await asyncio.sleep(interval)

    def stop_watching(self) -> None:
        """停止监控"""
        self._running = False
        if self._watch_task:
            self._watch_task.cancel()
            self._watch_task = None
        self._watch_callbacks.clear()
        logger.info("监控已停止")

    def auto_reply(
        self,
        condition: Callable[[Message], bool],
        reply: Callable[[Message], str],
        interval: float = 2.0
    ) -> None:
        """
        自动回复（同步版本）

        Args:
            condition: 消息条件判断函数
            reply: 回复内容生成函数
            interval: 检查间隔（秒）
        """

        def handle_message(msg: Message):
            if msg.direction == MessageDirection.INCOMING:
                if condition(msg):
                    reply_text = reply(msg)
                    if reply_text:
                        self.send_text(msg.sender, reply_text)

        self.watch_messages(handle_message, interval)

    async def auto_reply_async(
        self,
        condition: Callable[[Message], bool],
        reply: Callable[[Message], str],
        interval: float = 2.0
    ) -> None:
        """
        自动回复（异步版本）

        Args:
            condition: 消息条件判断函数
            reply: 回复内容生成函数
            interval: 检查间隔（秒）
        """

        async def handle_message(msg: Message):
            if msg.direction == MessageDirection.INCOMING:
                if condition(msg):
                    reply_text = reply(msg)
                    if reply_text:
                        await self.send_text_async(msg.sender, reply_text)

        await self.start_watching(handle_message, interval)

    def close(self) -> None:
        """关闭客户端，释放资源"""
        self.stop_watching()
        logger.info("iMessage 客户端已关闭")


class iMessageAPI:
    """
    iMessage 外部接口类

    提供简化的 API 供其他模块调用
    """

    def __init__(self):
        self._client: Optional[iMessageClient] = None

    def init(self) -> bool:
        """初始化客户端"""
        if sys.platform != "darwin":
            logger.warning("iMessage 仅支持 macOS")
            return False

        try:
            self._client = iMessageClient()
            logger.info("iMessage 客户端初始化成功")
            return True
        except Exception as e:
            logger.error(f"初始化 iMessage 客户端失败: {e}")
            return False

    def send(self, recipient: str, message: str) -> bool:
        """发送消息"""
        if not self._client:
            if not self.init():
                return False
        return self._client.send_text(recipient, message)

    def send_attachment(self, recipient: str, file_path: str) -> bool:
        """发送附件"""
        if not self._client:
            if not self.init():
                return False
        return self._client.send_attachment(recipient, file_path)

    def get_messages(self, limit: int = 100) -> List[Message]:
        """获取消息"""
        if not self._client:
            if not self.init():
                return []
        return self._client.get_messages(limit)

    def watch(self, callback: Callable[[Message], None], interval: float = 2.0) -> None:
        """监控消息"""
        if not self._client:
            if not self.init():
                return
        self._client.start_watching(callback, interval)

    def stop(self) -> None:
        """停止监控"""
        if self._client:
            self._client.close()
            self._client = None


# 全局 API 实例
api = iMessageAPI()


class IMessagerCLI:
    """
    iMessage 命令行工具

    用于从 iMessage 数据库拉取消息并打印
    """

    def __init__(self, limit: int = 20):
        """
        初始化

        Args:
            limit: 拉取消息数量，默认 20 条
        """
        self.limit = limit
        self.logger = logging.getLogger(__name__)

    def run(self, skip_empty: bool = True):
        """
        运行命令行工具

        Args:
            skip_empty: 是否跳过空消息（附件/图片），默认 True
        """
        if sys.platform != "darwin":
            self.logger.error("iMessage 仅支持 macOS 系统")
            return

        self.logger.info("=" * 50)
        self.logger.info("iMessage 消息拉取工具")
        self.logger.info("=" * 50)

        try:
            client = iMessageClient()
            self.logger.info(f"数据库路径: {client.db_path}")

            if skip_empty:
                # 直接查询有文本的消息（使用原生 SQL）
                import sqlite3
                conn = sqlite3.connect(client.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # 按 date 时间戳倒序，获取最近的消息
                query = """
                    SELECT ROWID, guid, text, handle_id, service, type, date,
                           is_delivered, is_read, is_played, is_from_me
                    FROM message
                    WHERE text IS NOT NULL AND text != ''
                    ORDER BY date DESC
                    LIMIT ?
                """
                cursor.execute(query, (self.limit,))
                rows = cursor.fetchall()
                conn.close()

                messages = []
                for row in rows:
                    # 使用全局导入的 Message 类
                    msg = Message(
                        id=row["ROWID"],
                        guid=row["guid"] or "",
                        text=row["text"] or "",
                        sender="",
                        receiver="",
                        timestamp=Message._mac_timestamp_to_datetime(row["date"]),
                        direction=MessageDirection.OUTGOING if row["is_from_me"] else MessageDirection.INCOMING,
                        message_type=MessageType.TEXT if row["type"] == 0 else MessageType.UNKNOWN,
                    )
                    # 获取联系人
                    if msg.direction == MessageDirection.OUTGOING:
                        msg.receiver = client._parse_handle_id(row["handle_id"]) if row["handle_id"] else ""
                    else:
                        msg.sender = client._parse_handle_id(row["handle_id"]) if row["handle_id"] else ""

                    messages.append(msg)

                self.logger.info(f"获取到 {len(messages)} 条最近文本消息")
            else:
                messages = client.get_messages(limit=self.limit)
                self.logger.info(f"获取到 {len(messages)} 条消息")

            self.logger.info("-" * 50)

            for i, msg in enumerate(messages[:self.limit], 1):
                self._print_message(msg, i)

            self.logger.info("-" * 50)
            self.logger.info("完成")

        except Exception as e:
            self.logger.error(f"获取消息失败: {e}")
            import traceback
            traceback.print_exc()

    def _print_message(self, msg: Message, index: int = 1):
        """打印单条消息"""
        # 获取发送者/接收者信息
        if msg.direction == MessageDirection.OUTGOING:
            contact = msg.receiver or "未知"
        else:
            contact = msg.sender or "未知"

        # 处理文本内容
        if msg.text:
            text = msg.text
            if len(text) > 100:
                text = text[:100] + "..."
        else:
            text = f"[{msg.message_type.value}]"

        # 格式化时间
        time_str = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")

        self.logger.info(f"[{index}] {msg.direction.value.upper()} | {contact}")
        self.logger.info(f"    时间: {time_str}")
        self.logger.info(f"    内容: {text}")


def main():
    """
    主入口函数
    """
    logger = logging.getLogger(__name__)

    client = iMessageClient()

    # 查找"测试"消息
    import sqlite3
    conn = sqlite3.connect(client.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ROWID, guid, text, handle_id, service, type, date, is_from_me
        FROM message
        WHERE text = '测试' AND is_from_me = 0
        ORDER BY date DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()

    if row:
        handle_id = row["handle_id"]
        sender = client._parse_handle_id(handle_id) if handle_id else ""

        logger.info("=" * 50)
        logger.info(f"找到测试消息 ROWID: {row['ROWID']}")
        logger.info(f"handle_id: {handle_id}")
        logger.info(f"解析的发送者: {sender}")

        if sender:
            logger.info(f"将回复给: {sender}")
            logger.info("回复内容: 你好")
            success = client.send_text(sender, "你好")
            if success:
                logger.info("回复成功！")
            else:
                logger.error("回复失败 - AppleScript 执行异常")
        else:
            logger.warning("无法获取发送者信息，无法回复")
    else:
        logger.info("没有找到测试消息或测试消息是自己发送的")


if __name__ == "__main__":
    main()
