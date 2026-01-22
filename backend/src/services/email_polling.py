"""
邮件轮询服务

异步轮询多邮箱未读邮件，生成摘要并发送 RPA 通知
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import List

from src.models.email import Email, EmailAccount, EmailSummary
from src.services.email import EmailService
from src.services.database import save_email, DatabaseService
from src.agents.email_summary import generate_email_summary
from src.utils.reply_sender import send_reply

logger = logging.getLogger(__name__)

# 邮件RPA通知模板
EMAIL_RPA_TEMPLATE = """📧 [{email_account}] 收到新邮件

🔔 重要性：{importance}
👤 发件人：{sender_name} &lt;{sender}&gt;
📌 主题：{subject}

📝 摘要：
{summary}

⏰ 时间：{time}
---
来自 SaveHelper 邮件提醒"""

# 无摘要通知
EMAIL_RPA_SIMPLE_TEMPLATE = """📧 [{email_account}] 收到新邮件

👤 发件人：{sender_name} &lt;{sender}&gt;
📌 主题：{subject}

📄 预览：
{preview}

⏰ 时间：{time}
---
来自 SaveHelper 邮件提醒"""


def _importance_emoji(importance: str) -> str:
    """重要性图标"""
    mapping = {
        "high": "🔴 高",
        "medium": "🟡 中",
        "low": "🟢 低"
    }
    return mapping.get(importance, "⚪ 未知")


async def _send_email_notification(email: Email, summary: EmailSummary = None):
    """发送邮件通知"""
    try:
        # 格式化时间
        time_str = datetime.fromtimestamp(email.received_at).strftime('%Y-%m-%d %H:%M')

        # 发件人显示
        sender_name = email.sender_name or "未知"
        sender = email.sender or ""

        if summary:
            importance_emoji = _importance_emoji(summary.importance)
            action_items_text = ""
            if summary.action_items:
                action_items_text = "\n待办事项：\n" + "\n".join(
                    f"  • {item}" for item in summary.action_items
                )

            message = EMAIL_RPA_TEMPLATE.format(
                email_account=email.email_account,
                importance=importance_emoji,
                sender_name=sender_name,
                sender=sender,
                subject=email.subject or "(无主题)",
                summary=summary.summary,
                time=time_str
            )
            if action_items_text:
                message += action_items_text
        else:
            message = EMAIL_RPA_SIMPLE_TEMPLATE.format(
                email_account=email.email_account,
                sender_name=sender_name,
                sender=sender,
                subject=email.subject or "(无主题)",
                preview=email.preview,
                time=time_str
            )

        # 发送通知（使用特殊的 email source）
        from src.models.chat_record import UnifiedMessage
        fake_msg = UnifiedMessage(
            msg_id=f"email_{email.uid}_{email.received_at}",
            source="email_notification",
            msg_type="text",
            content=message,
            from_user=email.sender,
            create_time=int(time.time()),
            raw_data=email.model_dump()
        )

        await send_reply(fake_msg, message)
        logger.info(f"[EmailPolling] 通知已发送: {email.subject}")

    except Exception as e:
        logger.error(f"[EmailPolling] 发送通知失败: {e}")


async def process_email(email: Email) -> bool:
    """
    处理单封邮件

    Returns:
        是否处理成功
    """
    try:
        logger.info(f"[EmailPolling] 处理邮件: {email.subject[:50]}...")

        # 1. 生成摘要（如果正文不为空）
        summary = None
        if email.preview:
            try:
                summary = generate_email_summary(email.subject, email.preview)
            except Exception as e:
                logger.warning(f"[EmailPolling] 生成摘要失败: {e}")

        # 2. 落库
        try:
            save_email(email, summary)
            logger.info(f"[EmailPolling] 邮件已保存: {email.uid}")
        except Exception as e:
            logger.error(f"[EmailPolling] 保存邮件失败: {e}")

        # 3. 发送 RPA 通知
        await _send_email_notification(email, summary)

        return True

    except Exception as e:
        logger.error(f"[EmailPolling] 处理邮件异常: {e}", exc_info=True)
        return False


def get_account_config(account: str) -> EmailAccount:
    """
    从环境变量获取邮箱配置

    环境变量格式（分号分隔多邮箱）：
    EMAIL_ACCOUNTS=acc1@qq.com;acc2@qq.com
    EMAIL_IMAP_SERVERS=imap.qq.com;imap.qq.com
    EMAIL_IMAP_PORTS=993;993
    EMAIL_AUTHORIZATION_CODES=code1;code2
    """
    accounts = os.getenv("EMAIL_ACCOUNTS", "").split(";")
    servers = os.getenv("EMAIL_IMAP_SERVERS", "").split(";")
    ports = os.getenv("EMAIL_IMAP_PORTS", "993").split(";")
    codes = os.getenv("EMAIL_AUTHORIZATION_CODES", "").split(";")

    # 查找对应账号的配置
    idx = -1
    for i, acc in enumerate(accounts):
        if acc.strip() == account:
            idx = i
            break

    if idx < 0:
        raise ValueError(f"未找到邮箱配置: {account}")

    server = servers[idx].strip() if idx < len(servers) else servers[0].strip()
    port = int(ports[idx].strip()) if idx < len(ports) else 993
    code = codes[idx].strip() if idx < len(codes) else ""

    folder = os.getenv("EMAIL_FOLDER", "INBOX")

    return EmailAccount(
        account=account,
        imap_server=server,
        imap_port=port,
        authorization_code=code,
        folder=folder
    )


def get_last_offset(account: str) -> tuple:
    """
    获取邮箱的最后偏移量

    Returns:
        (last_uid, last_uid_time)
    """
    try:
        with DatabaseService.get_connection() as conn:
            row = conn.execute(
                "SELECT last_uid, last_uid_time FROM email_accounts WHERE account = ?",
                (account,)
            ).fetchone()
            if row:
                return int(row[0]), int(row[1])
    except Exception as e:
        logger.warning(f"[EmailPolling] 获取偏移量失败: {e}")

    # 从数据库邮件表获取最大 UID
    try:
        with DatabaseService.get_connection() as conn:
            row = conn.execute(
                "SELECT MAX(CAST(uid AS INTEGER)), received_at FROM emails WHERE email_account = ?",
                (account,)
            ).fetchone()
            if row and row[0]:
                return int(row[0]), int(row[1]) if row[1] else 0
    except Exception as e:
        logger.warning(f"[EmailPolling] 查询最大 UID 失败: {e}")

    return 0, 0


def save_last_offset(account: str, uid: int, uid_time: int):
    """保存偏移量到数据库"""
    try:
        with DatabaseService.get_connection() as conn:
            # 更新或插入
            existing = conn.execute(
                "SELECT id FROM email_accounts WHERE account = ?", (account,)
            ).fetchone()

            if existing:
                conn.execute(
                    """UPDATE email_accounts SET last_uid = ?, last_uid_time = ?, updated_at = ?
                       WHERE account = ?""",
                    (uid, uid_time, int(time.time()), account)
                )
            else:
                conn.execute(
                    """INSERT INTO email_accounts (account, imap_server, imap_port, authorization_code, folder, last_uid, last_uid_time)
                       VALUES (?, '', 993, '', 'INBOX', ?, ?)""",
                    (account, uid, uid_time)
                )
            conn.commit()
    except Exception as e:
        logger.error(f"[EmailPolling] 保存偏移量失败: {e}")


async def run_email_polling():
    """
    邮件轮询主循环
    """
    logger.info(">>> Email Polling Service Starting... <<<")

    accounts = os.getenv("EMAIL_ACCOUNTS", "").split(";")
    if not accounts or not accounts[0]:
        logger.warning("[EmailPolling] 未配置邮箱账号，轮询服务已停止。")
        return

    interval = int(os.getenv("EMAIL_CHECK_INTERVAL", "60"))

    logger.info(f"[EmailPolling] 已配置 {len(accounts)} 个邮箱账号")

    while True:
        try:
            for account in accounts:
                account = account.strip()
                if not account:
                    continue

                logger.info(f"[EmailPolling] 检查邮箱: {account}")

                # 获取配置和偏移量
                try:
                    email_account = get_account_config(account)
                except Exception as e:
                    logger.error(f"[EmailPolling] 获取邮箱配置失败: {e}")
                    continue

                last_uid, last_uid_time = get_last_offset(account)
                logger.info(f"[EmailPolling] 偏移量: uid={last_uid}, time={last_uid_time}")

                # 拉取邮件
                service = EmailService(email_account)
                emails = service.fetch_unread(since_uid=last_uid, limit=50)

                if emails:
                    logger.info(f"[EmailPolling] 拉取到 {len(emails)} 封新邮件")

                    for email in emails:
                        await process_email(email)

                    # 更新偏移量
                    latest_email = emails[0]  # 按时间倒序，第一封最新
                    save_last_offset(
                        account,
                        int(latest_email.uid),
                        latest_email.received_at
                    )
                else:
                    logger.debug(f"[EmailPolling] 没有新邮件")

            # 等待下次检查
            await asyncio.sleep(interval)

        except Exception as e:
            logger.error(f"[EmailPolling] 轮询主循环错误: {e}", exc_info=True)
            await asyncio.sleep(15)
