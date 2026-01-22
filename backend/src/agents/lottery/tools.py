"""
抽奖 Agent - 数据库工具
"""
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from datetime import datetime
from src.services.database import get_connection
import logging

logger = logging.getLogger(__name__)

class TodayParticipantsToolInput(BaseModel):
    """Input for TodayParticipantsTool."""
    pass

class TodayParticipantsTool(BaseTool):
    name: str = "TodayParticipantsTool"
    description: str = "获取今天所有报名抽奖的人员名单"
    args_schema: Type[BaseModel] = TodayParticipantsToolInput

    def _run(self) -> str:
        today_str = datetime.now().strftime('%Y-%m-%d')
        # SQLite datetime usually matches prefix 'YYYY-MM-DD'
        query = "SELECT name FROM lottery_participants WHERE date(created_at) = ?"

        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (today_str,))
                rows = cursor.fetchall()
                names = [row['name'] for row in rows]

                if not names:
                    return "今天还没有人报名抽奖。"

                return "\n".join(names)
        except Exception as e:
            logger.error(f"Error fetching participants: {e}")
            return f"获取名单失败: {e}"
