"""
Craft 保存路由
"""
import asyncio
import logging
import threading

from fastapi import APIRouter, HTTPException

from src.services.craft import save_blocks_to_craft
from src.services.todo_reminder import run_todo_reminder
from src.models.craft import CraftMessage

logger = logging.getLogger(__name__)

craft_router = APIRouter(prefix="/craft", tags=["Craft"])


@craft_router.post("/save")
async def craft_save(message: CraftMessage):
    """保存消息到 Craft"""
    try:
        block = {"type": "text", "markdown": message.message}
        await save_blocks_to_craft([block])
        return {"status": "success", "message": "Saved to Craft"}
    except Exception as e:
        logger.error(f"[Craft] 保存失败: {e}")
        raise HTTPException(status_code=500, detail="Failed to save to Craft")


@craft_router.post("/todo-reminder/test")
async def test_todo_reminder():
    """
    测试待办提醒功能
    手动触发搜索当天待办任务并发送提醒
    """
    logger.info("收到待办提醒测试请求...")

    # 在后台线程中执行
    thread = threading.Thread(target=asyncio.run, args=(run_todo_reminder(),))
    thread.start()

    return {
        "status": "success",
        "message": "待办提醒测试任务已启动，请查看日志和企微通知"
    }
