import logging
import asyncio
from datetime import date
from src.handlers.base import BaseHandler
from src.models.chat_record import UnifiedMessage
from src.services.craft import add_collection_item

logger = logging.getLogger(__name__)

# Craft Collection ID for 新闻播报
NEWS_COLLECTION_ID = "D16638DF-93AD-41B2-AFA8-30E19A968942"

class NewsHandler(BaseHandler):
    """
    处理新闻播报指令
    Priority: 2
    """
    async def check(self, msg: UnifiedMessage) -> bool:
        return msg.msg_type == "text" and "新闻播报" in msg.content

    async def handle(self, msg: UnifiedMessage):
        logger.info(f"[NewsHandler] Processing news request: {msg.msg_id}")
        
        # 1. 立即回复确认
        await self.reply(msg, "🤖 收到新闻播报请求，正在采编中，请稍候...")
        
        # Lazy import inside handle to avoid startup issues
        from src.agents.news import run_news_crew
        
        try:
            # 2. 生成新闻 (异步执行)
            logger.info("[NewsHandler] Starting news generation...")
            # 使用 asyncio.to_thread 运行同步的 Crew 代码
            script_result = await asyncio.to_thread(run_news_crew)
            
            # 3. 回复结果
            today_str = date.today().isoformat()
            final_text = f"📢 **今日新闻播报** ({today_str})\n\n{script_result}"
            await self.reply(msg, final_text)
            
            # 4. 保存到 Craft News Collection (独立存储，不走通用收件箱)
            items = [
                {
                    "title": f"新闻播报 - {today_str}",
                    "properties": {
                        "": today_str,
                        "_2": script_result
                    }
                }
            ]
            await add_collection_item(NEWS_COLLECTION_ID, items)
            logger.info("[NewsHandler] News saved to Collection.")
            
        except Exception as e:
            logger.error(f"[NewsHandler] Failed: {e}", exc_info=True)
            await self.reply(msg, f"⚠️ 新闻生成遇到问题: {str(e)}")
