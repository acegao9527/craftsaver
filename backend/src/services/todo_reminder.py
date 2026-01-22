"""
Craft 待办提醒服务

每天定时检索 Craft 文档中当天的未完成待办任务，发送 RPA 提醒
"""
import asyncio
import logging
import os
from typing import List, Dict

from src.services.craft import fetch_todo_blocks, filter_today_todos
from src.utils.reply_sender import _send_rpa_notification

logger = logging.getLogger("src.services.todo_reminder")


def is_todo_enabled() -> bool:
    """检查是否启用待办提醒"""
    return os.getenv("CRAFT_TODO_ENABLED", "").lower() == "true"


def get_remind_time() -> str:
    """获取提醒时间"""
    return os.getenv("CRAFT_TODO_REMIND_TIME", "09:00")


def format_todo_message(todos: List[Dict], today: str) -> str:
    """格式化待办提醒消息"""
    if not todos:
        return f"✅ 今天 ({today}) 没有待办任务"

    lines = [f"📋 Craft 待办提醒 ({today})\n"]
    lines.append("-" * 30)

    for i, todo in enumerate(todos, 1):
        doc_name = todo.get("doc_name", "未知文档")
        text = todo.get("text", "").strip()
        if len(text) > 50:
            text = text[:50] + "..."
        lines.append(f"{i}. [{doc_name}] {text}")

    lines.append("-" * 30)
    lines.append(f"共 {len(todos)} 个待办项")
    lines.append("---")
    lines.append("来自 SaveHelper 待办提醒")

    return "\n".join(lines)


async def run_todo_reminder():
    """执行待办提醒"""
    logger.info("[TodoReminder] 开始检查待办任务...")

    if not is_todo_enabled():
        logger.info("[TodoReminder] 待办提醒未启用，跳过")
        return

    today = os.getenv("TODAY_DATE") or asyncio.get_event_loop().run_in_executor(
        None, lambda: __import__("datetime").datetime.now().strftime("%Y-%m-%d")
    )
    if isinstance(today, asyncio.Future):
        today = await today

    logger.info(f"[TodoReminder] 检查日期: {today}")

    blocks = fetch_todo_blocks()

    if not blocks:
        logger.info("[TodoReminder] 没有获取到 blocks")
        await _send_rpa_notification(format_todo_message([], today))
        return

    todos = filter_today_todos(blocks, today)

    for i, todo in enumerate(todos, 1):
        block_id = todo.get("block_id", "")[:20]
        text = (todo.get("text", "") or "(空)")[:60]
        doc_name = todo.get("doc_name", "未知")
        logger.info(f"[TodoReminder]   [{i}] blockId={block_id}... text=\"{text}\" doc=\"{doc_name}\"")

    logger.info(f"[TodoReminder] 找到 {len(todos)} 个待办项")

    message = format_todo_message(todos, today)
    await _send_rpa_notification(message)

    logger.info("[TodoReminder] 提醒发送完成")


if __name__ == "__main__":
    asyncio.run(run_todo_reminder())
