"""
生日管理 API
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)
birthday_router = APIRouter(prefix="/birthday", tags=["Birthday"])

# 复用 admin 的依赖
from src.api.deps import verify_token

class BirthdayCreate(BaseModel):
    name: str
    birth_date: str # YYYY-MM-DD
    calendar_type: str = "solar" # solar, lunar
    note: Optional[str] = None

class BirthdayUpdate(BaseModel):
    name: Optional[str] = None
    birth_date: Optional[str] = None
    calendar_type: Optional[str] = None
    note: Optional[str] = None

@birthday_router.get("/list")
async def list_birthdays(
    page: int = 1,
    size: int = 10,
    name: Optional[str] = None,
    token_info: dict = Depends(verify_token)
):
    """获取生日列表"""
    try:
        from src.services.database import DatabaseService
        conn = DatabaseService.get_connection()
        cursor = conn.cursor()

        # 构建查询条件
        conditions = ["1=1"]
        params = []
        if name:
            conditions.append("name LIKE ?")
            params.append(f"%{name}%")

        where = " AND ".join(conditions)
        offset = (page - 1) * size

        # 查询总数
        cursor.execute(f"SELECT COUNT(*) FROM birthday_reminders WHERE {where}", params)
        total = cursor.fetchone()[0]

        # 查询列表
        query = f"SELECT id, name, birth_date, calendar_type, note, created_at FROM birthday_reminders WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([size, offset])
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        data = []
        for row in rows:
            data.append({
                "id": row[0],
                "name": row[1],
                "birth_date": row[2],
                "calendar_type": row[3],
                "note": row[4],
                "created_at": row[5]
            })

        return {"code": 200, "data": {"list": data, "total": total}}
    except Exception as e:
        logger.error(f"[Admin] 获取生日列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@birthday_router.get("/today")
async def get_today_birthdays(token_info: dict = Depends(verify_token)):
    """获取今日生日"""
    try:
        # 复用 Service 逻辑 (需要计算农历等)
        from src.birthday_reminder.service import BirthdayService
        reminders = BirthdayService.list_reminders()
        
        data = []
        for r in reminders:
            try:
                birth_date = datetime.strptime(r['birth_date'], "%Y-%m-%d").date()
                info = BirthdayService.calculate_next_birthday(birth_date, r['calendar_type'])
                if info and info['is_today']:
                     data.append({
                         "id": r['id'],
                         "name": r['name'],
                         "age": info['age']
                     })
            except Exception as e:
                logger.error(f"Error calculating birthday for {r['name']}: {e}")

        return {"code": 200, "data": data}
    except Exception as e:
        logger.error(f"[Admin] 获取今日生日失败: {e}")
        return {"code": 200, "data": []}


@birthday_router.post("")
async def create_birthday(data: BirthdayCreate, token_info: dict = Depends(verify_token)):
    """添加生日"""
    try:
        from src.services.database import DatabaseService
        conn = DatabaseService.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO birthday_reminders (name, birth_date, calendar_type, note) VALUES (?, ?, ?, ?)",
            (data.name, data.birth_date, data.calendar_type, data.note)
        )
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()

        logger.info(f"[Admin] 添加生日: {data.name}")
        return {"code": 200, "data": {"id": new_id}, "message": "添加成功"}
    except Exception as e:
        logger.error(f"[Admin] 添加生日失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@birthday_router.put("/{id}")
async def update_birthday(id: int, data: BirthdayUpdate, token_info: dict = Depends(verify_token)):
    """更新生日"""
    try:
        from src.services.database import DatabaseService
        conn = DatabaseService.get_connection()
        cursor = conn.cursor()

        # 构建更新语句
        updates = []
        params = []
        if data.name is not None:
            updates.append("name = ?")
            params.append(data.name)
        if data.birth_date is not None:
            updates.append("birth_date = ?")
            params.append(data.birth_date)
        if data.calendar_type is not None:
            updates.append("calendar_type = ?")
            params.append(data.calendar_type)
        if data.note is not None:
            updates.append("note = ?")
            params.append(data.note)

        if not updates:
            return {"code": 200, "message": "无更新"}

        params.append(id)
        cursor.execute(f"UPDATE birthday_reminders SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        conn.close()

        logger.info(f"[Admin] 更新生日 ID: {id}")
        return {"code": 200, "message": "更新成功"}
    except Exception as e:
        logger.error(f"[Admin] 更新生日失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@birthday_router.delete("/{id}")
async def delete_birthday(id: int, token_info: dict = Depends(verify_token)):
    """删除生日"""
    try:
        from src.services.database import DatabaseService
        conn = DatabaseService.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM birthday_reminders WHERE id = ?", (id,))
        conn.commit()
        conn.close()

        logger.info(f"[Admin] 删除生日 ID: {id}")
        return {"code": 200, "message": "删除成功"}
    except Exception as e:
        logger.error(f"[Admin] 删除生日失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))