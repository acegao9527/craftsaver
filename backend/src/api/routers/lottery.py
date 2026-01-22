from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
from src.services.database import get_connection
import logging

router = APIRouter(prefix="/api/lottery", tags=["Lottery"])
logger = logging.getLogger(__name__)

class JoinRequest(BaseModel):
    name: str

@router.post("/join")
async def join_lottery(req: JoinRequest):
    """
    报名参加抽奖
    """
    if not req.name or len(req.name.strip()) == 0:
        raise HTTPException(status_code=400, detail="姓名不能为空")

    name = req.name.strip()
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            # Optional: Check if already joined today? 
            # The requirements didn't specify unique constraints per day per person, 
            # but the Agent is supposed to dedup. Let's allow multiple inserts and let Agent handle it,
            # or maybe just insert.
            
            sql = "INSERT INTO lottery_participants (name, created_at) VALUES (?, ?)"
            cursor.execute(sql, (name, created_at))
            conn.commit()
            
        return {
            "code": 200,
            "data": {
                "message": "报名成功",
                "name": name
            }
        }
    except Exception as e:
        logger.error(f"Failed to join lottery: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")
