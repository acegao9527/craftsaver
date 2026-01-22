"""
邮件服务

IMAP 协议拉取邮件，支持多邮箱配置
"""
import email
import imaplib
import logging
import time
from email.header import decode_header
from typing import List, Optional
import quopri
import chardet

from src.models.email import Email, EmailAccount

# 使用轮询日志器
logger = logging.getLogger("src.services.email_polling")


class EmailService:
    """邮件服务"""

    def __init__(self, account: EmailAccount):
        self.account = account
        self.conn: Optional[imaplib.IMAP4_SSL] = None

    def connect(self) -> bool:
        """连接 IMAP 服务器"""
        try:
            logger.info(f"[EmailPolling] 连接 {self.account.imap_server}:{self.account.imap_port}...")
            self.conn = imaplib.IMAP4_SSL(
                host=self.account.imap_server,
                port=self.account.imap_port
            )
            self.conn.login(self.account.account, self.account.authorization_code)
            logger.info(f"[EmailPolling] 连接成功: {self.account.account}")
            return True
        except Exception as e:
            logger.error(f"[EmailPolling] 连接失败: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self.conn:
            try:
                self.conn.logout()
            except:
                pass
            self.conn = None
            logger.info(f"[EmailPolling] 已断开: {self.account.account}")

    def _decode_header(self, header: str) -> str:
        """解码邮件头"""
        if not header:
            return ""
        try:
            decoded = decode_header(header)
            parts = []
            for part, encoding in decoded:
                if isinstance(part, bytes):
                    if encoding:
                        part = part.decode(encoding)
                    else:
                        part = part.decode('utf-8', errors='ignore')
                parts.append(part)
            return ''.join(parts)
        except Exception as e:
            logger.warning(f"[EmailPolling] 解码 header 失败: {e}")
            return header or ""

    def _get_email_body(self, msg) -> str:
        """提取邮件正文（纯文本）"""
        body = ""
        html_body = ""

        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get('Content-Disposition'))

            # 忽略附件
            if 'attachment' in content_disposition:
                continue

            try:
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue

                if content_type == 'text/plain':
                    # 检测编码
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        body = payload.decode(charset, errors='ignore')
                    except:
                        # 尝试自动检测
                        detected = chardet.detect(payload)
                        if detected['encoding']:
                            body = payload.decode(detected['encoding'], errors='ignore')
                        else:
                            body = payload.decode('utf-8', errors='ignore')

                elif content_type == 'text/html':
                    # 暂不处理 HTML
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        html_body = payload.decode(charset, errors='ignore')
                    except:
                        pass
            except Exception as e:
                logger.debug(f"[EmailPolling] 解析邮件部分失败: {e}")
                continue

        # 如果没有纯文本，尝试从 HTML 提取
        if not body and html_body:
            import re
            # 简单提取文本
            body = re.sub(r'<[^>]+>', '', html_body)
            body = re.sub(r'\s+', ' ', body).strip()

        return body

    def fetch_unread(self, since_uid: int = 0, limit: int = 50) -> List[Email]:
        """
        拉取未读邮件

        Args:
            since_uid: 只拉取 UID 大于此值的邮件
            limit: 最大返回数量

        Returns:
            邮件列表（按收件时间倒序）
        """
        if not self.conn and not self.connect():
            return []

        try:
            # 选择文件夹
            self.conn.select(self.account.folder, readonly=False)

            # 使用 UID search
            # 构建搜索条件: UID range AND UNSEEN
            # 注意: UID 范围格式为 "start:*"
            search_criteria = ['UNSEEN']
            if since_uid > 0:
                search_criteria.append(f'UID {since_uid + 1}:*')
            
            # 使用 uid 方法进行搜索
            status, response = self.conn.uid('search', None, *search_criteria)

            if status != 'OK':
                logger.error(f"[EmailPolling] 搜索邮件失败: {status}")
                return []

            # response[0] 包含所有匹配的 UID，空格分隔
            uids = response[0].split()
            if not uids:
                return []

            logger.info(f"[EmailPolling] 找到 {len(uids)} 封未读邮件 (since_uid={since_uid})")

            emails = []
            count = 0

            # 倒序处理（最新的先处理）
            # uids 是字节列表
            for uid_bytes in reversed(uids):
                if count >= limit:
                    break

                uid = int(uid_bytes)
                # 双重检查 UID (虽然服务器搜索应该已经过滤了)
                if uid <= since_uid:
                    continue

                try:
                    # 使用 UID fetch 获取邮件内容
                    # RFC822 获取完整内容
                    status, msg_data = self.conn.uid('fetch', uid_bytes, '(RFC822)')
                    if status != 'OK' or not msg_data:
                        continue

                    # msg_data 结构通常是 [ (b'1 (UID 123 RFC822 {size}', b'content'), b')' ]
                    # 或者是 [ (b'UID 123 RFC822 {size}', b'content') ] 取决于服务器
                    # 我们主要关心其中的 tuple 部分，它的第二个元素是 content
                    raw_email = None
                    for part in msg_data:
                        if isinstance(part, tuple):
                            raw_email = part[1]
                            break
                    
                    if not raw_email:
                        continue

                    msg = email.message_from_bytes(raw_email)

                    # 提取邮件信息
                    subject = self._decode_header(msg.get('Subject', ''))
                    sender = self._decode_header(msg.get('From', ''))

                    # 解析发件人
                    sender_name = ""
                    sender_email = sender
                    if '<' in sender and '>' in sender:
                        sender_name = sender.split('<')[0].strip().strip('"')
                        sender_email = sender.split('<')[1].strip('>')
                    else:
                        sender_email = sender.strip()

                    # 解析日期
                    date_str = msg.get('Date', '')
                    received_at = int(time.time())
                    try:
                        from email.utils import parsedate_to_datetime
                        dt = parsedate_to_datetime(date_str)
                        received_at = int(dt.timestamp())
                    except Exception as e:
                        logger.debug(f"[EmailPolling] 解析日期失败: {e}")

                    # 提取正文
                    body = self._get_email_body(msg)

                    # 生成 200 字预览
                    preview = body[:200].strip()
                    if len(body) > 200:
                        preview += '...'

                    email_obj = Email(
                        email_account=self.account.account,
                        uid=str(uid),
                        subject=subject,
                        sender=sender_email,
                        sender_name=sender_name,
                        received_at=received_at,
                        preview=preview,
                        raw_content=raw_email.decode('utf-8', errors='ignore')
                    )

                    emails.append(email_obj)
                    count += 1

                except Exception as e:
                    logger.error(f"[EmailPolling] 解析邮件失败(UID={uid}): {e}")
                    continue

            # 按收件时间倒序
            emails.sort(key=lambda x: x.received_at, reverse=True)
            logger.info(f"[EmailPolling] 实际返回 {len(emails)} 封邮件")

            return emails

        except Exception as e:
            logger.error(f"[EmailPolling] 拉取邮件失败: {e}", exc_info=True)
            return []
        finally:
            self.disconnect()


def parse_sender(sender: str) -> tuple:
    """
    解析发件人字符串

    Returns:
        (sender_name, sender_email)
    """
    if not sender:
        return "", ""

    if '<' in sender and '>' in sender:
        name = sender.split('<')[0].strip().strip('"')
        email = sender.split('<')[1].strip('>')
        return name, email

    return "", sender
