from fastapi import APIRouter, BackgroundTasks
# from src.crew_news.crew import run_news_crew # Removed for lazy loading
from src.services.craft import add_collection_item
# from src.services.telegram import send_telegram_message # Removed as per request
from src.utils.reply_sender import _send_rpa_notification
from datetime import date
import logging
import time
import asyncio
import os

logger = logging.getLogger(__name__)
news_router = APIRouter(prefix="/news", tags=["News"])

# Craft Collection ID for 新闻播报
NEWS_COLLECTION_ID = "D16638DF-93AD-41B2-AFA8-30E19A968942"

def process_news_generation_task():
    """
    后台任务处理函数
    """
    logger.info("开始在后台执行 Agent 任务...")

    # Lazy import to avoid startup crash due to C-extension conflict
    from src.agents.news import run_news_crew

    start_time = time.time()
    try:
        # 直接调用同步函数，FastAPI 会在线程池中运行此任务
        script_result = run_news_crew()

        duration = time.time() - start_time
        logger.info(f"新闻稿生成成功，耗时 {duration:.2f} 秒。")
        logger.info(f"=== 生成的新闻稿内容 ===\n{script_result}\n========================")

        # 发送到 WeCom RPA
        logger.info(f"Sending news report to WeCom RPA...")
        try:
            rpa_text = f"📢 **今日新闻播报** ({date.today().isoformat()})\n\n{script_result}"
            asyncio.run(_send_rpa_notification(rpa_text))
            logger.info("WeCom RPA notification sent request submitted.")
        except Exception as e:
            logger.error(f"Failed to send WeCom RPA notification: {e}")

        # 构造 Collection 项
        today_str = date.today().isoformat() # YYYY-MM-DD
        items = [
            {
                "title": f"新闻播报 - {today_str}",
                "properties": {
                    "": today_str,      # 创建日期
                    "_2": script_result # 播报内容
                }
            }
        ]

        # 异步调用保存到 Collection
        asyncio.run(add_collection_item(NEWS_COLLECTION_ID, items))

    except Exception as e:
        logger.error(f"后台生成新闻稿时出错: {str(e)}", exc_info=True)

@news_router.post("/generate")
async def generate_news(background_tasks: BackgroundTasks):
    """
    触发幼儿园新闻 Agent 生成播报稿。
    立即返回响应，任务在后台异步执行，结果将打印在日志中。
    """
    logger.info("收到幼儿园新闻稿生成请求，正在加入后台任务队列...")

    background_tasks.add_task(process_news_generation_task)

    return {
        "status": "success",
        "message": "新闻稿生成任务已提交，正在后台处理中。请查看服务器日志获取结果。"
    }
