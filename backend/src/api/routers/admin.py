"""
管理后台 API 适配层
为前端 admin 提供统一的数据格式
"""
import os
import json
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import logging
from src.api.deps import verify_token, ACCESS_TOKENS

logger = logging.getLogger(__name__)
admin_router = APIRouter(prefix="/api/admin", tags=["Admin"])

# 子路由 - 挂载到 admin_router 下
from .admin_message import message_router
from .admin_birthday import birthday_router
from .admin_config import config_router
from .admin_binding import binding_router

admin_router.include_router(message_router)
admin_router.include_router(birthday_router)
admin_router.include_router(config_router)
admin_router.include_router(binding_router)

# 简单的 token 验证（生产环境应使用 JWT）
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "admin123456")
# ACCESS_TOKENS moved to deps.py
# security moved to deps.py


# ============ 认证模块 ============

class LoginRequest(BaseModel):
    username: str
    password: str


@admin_router.post("/auth/login")
async def admin_login(data: LoginRequest):
    """
    管理后台登录
    """
    # 简单验证（生产环境应使用加密验证）
    if data.username == "admin" and data.password == ADMIN_TOKEN:
        token = secrets.token_hex(32)
        ACCESS_TOKENS[token] = {
            "username": data.username,
            "expires_at": datetime.now() + timedelta(days=7)
        }
        logger.info(f"[Admin] 管理员登录成功")
        return {
            "code": 200,
            "data": {
                "token": token,
                "username": "admin"
            }
        }
    else:
        logger.warning(f"[Admin] 登录失败: {data.username}")
        raise HTTPException(status_code=401, detail="用户名或密码错误")


@admin_router.post("/auth/logout")
async def admin_logout(token_info: dict = Depends(verify_token)):
    """退出登录"""
    # 这里通过 header 获取 token
    return {"code": 200, "message": "退出成功"}


@admin_router.get("/auth/info")
async def get_admin_info(token_info: dict = Depends(verify_token)):
    """获取管理员信息"""
    return {
        "code": 200,
        "data": {
            "username": token_info["username"],
            "avatar": ""
        }
    }


# ============ Dashboard 模块 ============

@admin_router.get("/dashboard/stats")
async def get_dashboard_stats(token_info: dict = Depends(verify_token)):
    """获取仪表盘统计数据"""
    try:
        from src.services.database import DatabaseService
        conn = DatabaseService.get_connection()
        cursor = conn.cursor()

        # 总消息数
        cursor.execute("SELECT COUNT(*) FROM unified_messages")
        total_messages = cursor.fetchone()[0]

        # 今日消息数
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT(*) FROM unified_messages WHERE DATE(created_at) = ?", (today,))
        today_messages = cursor.fetchone()[0]

        # 今日生日 (复用 Service 计算)
        from src.birthday_reminder.service import BirthdayService
        reminders = BirthdayService.list_reminders()
        today_birthdays = 0
        for r in reminders:
            try:
                birth_date = datetime.strptime(r['birth_date'], "%Y-%m-%d").date()
                info = BirthdayService.calculate_next_birthday(birth_date, r['calendar_type'])
                if info and info['is_today']:
                     today_birthdays += 1
            except:
                pass

        # 联系人数量（不同发送者）
        cursor.execute("SELECT COUNT(DISTINCT from_user) FROM unified_messages")
        total_contacts = cursor.fetchone()[0]

        conn.close()

        return {
            "code": 200,
            "data": {
                "todayMessages": today_messages,
                "todayBirthdays": today_birthdays,
                "totalMessages": total_messages,
                "totalContacts": total_contacts
            }
        }
    except Exception as e:
        logger.error(f"[Admin] 获取统计失败: {e}")
        return {"code": 200, "data": {"todayMessages": 0, "todayBirthdays": 0, "totalMessages": 0, "totalContacts": 0}}


@admin_router.get("/dashboard/todos")
async def get_dashboard_todos(token_info: dict = Depends(verify_token)):
    """获取今日待办"""
    try:
        from src.services.todo_reminder import fetch_todo_blocks, filter_today_todos
        from src.services.weather import get_city_weather

        blocks = fetch_todo_blocks()
        today = datetime.now().strftime("%Y-%m-%d")
        todos = filter_today_todos(blocks, today)[:5]

        return {
            "code": 200,
            "data": todos
        }
    except Exception as e:
        logger.error(f"[Admin] 获取待办失败: {e}")
        return {"code": 200, "data": []}


@admin_router.get("/dashboard/birthdays")
async def get_dashboard_birthdays(token_info: dict = Depends(verify_token)):
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
