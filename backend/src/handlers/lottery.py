from .base import BaseHandler
from src.models.chat_record import UnifiedMessage
# from src.crew_lottery import get_lottery_crew # Lazy import
import logging
import asyncio

logger = logging.getLogger(__name__)

class LotteryHandler(BaseHandler):
    """
    处理“抽奖”关键字，触发 Agent 流程
    Priority: High (before Default, maybe same level as News)
    """
    
    async def check(self, msg: UnifiedMessage) -> bool:
        if not msg.content:
            return False
        return msg.content.strip() == "抽奖"

    async def handle(self, msg: UnifiedMessage):
        logger.info(f"[LotteryHandler] Triggered by {msg.msg_id}")
        
        # 1. 立即回复
        await self.reply(msg, "🎰 正在启动抽奖流程，各路 Agent 正在集结...\n报名官正在整理名单，抽奖官正在洗手，审计官正在准备印章，请稍候！")
        
        # 2. 异步执行 Crew 任务
        asyncio.create_task(self._run_crew(msg))

    async def _run_crew(self, msg: UnifiedMessage):
        try:
            logger.info("[LotteryHandler] Starting Crew...")
            # Lazy import to avoid startup crashes if CrewAI fails
            from src.agents.lottery import run_lottery_crew
            
            # Crew.kickoff() returns the result
            # Using to_thread to run blocking code
            final_output = await asyncio.to_thread(run_lottery_crew)
            
            logger.info(f"[LotteryHandler] Crew finished. Result: {final_output[:100]}...")
            
            await self.reply(msg, final_output)
            
        except ImportError as e:
            logger.error(f"[LotteryHandler] CrewAI import failed: {e}")
            await self.reply(msg, "⚠️ 抽奖服务暂时不可用 (组件加载失败)")
        except Exception as e:
            logger.error(f"[LotteryHandler] Crew execution failed: {e}", exc_info=True)
            await self.reply(msg, f"⚠️ 抽奖流程出错了: {str(e)}")
