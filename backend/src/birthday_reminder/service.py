import logging
import asyncio
from datetime import date, timedelta, datetime
from typing import List, Optional
from borax.calendars.lunardate import LunarDate
from src.services.database import DatabaseService
from src.birthday_reminder.models import BirthdayReminderCreate, BirthdayReminder
from src.utils.reply_sender import _send_rpa_notification

logger = logging.getLogger(__name__)

class BirthdayService:
    @staticmethod
    def _get_solar_date_from_lunar(year: int, month: int, day: int) -> date:
        """农历转公历"""
        try:
            lunar = LunarDate(year, month, day)
            return lunar.to_solar_date()
        except Exception as e:
            logger.error(f"[Birthday] Lunar conversion error: {year}-{month}-{day}: {e}")
            return None

    @staticmethod
    def calculate_next_birthday(birth_date: date, calendar_type: str) -> dict:
        """
        计算下一个生日的公历日期、倒计时天数、以及那一天是几岁
        
        Returns:
            {
                "next_solar_date": date,
                "days_until": int,
                "age": int (turning age),
                "is_today": bool
            }
        """
        today = date.today()
        current_year = today.year
        
        next_date = None
        turning_age = 0
        
        if calendar_type == 'solar':
            # 公历比较简单
            try:
                this_year_bday = birth_date.replace(year=current_year)
            except ValueError:
                # 处理 2月29日 生日但在非闰年的情况 -> 顺延到 3月1日
                this_year_bday = date(current_year, 3, 1)
                
            if this_year_bday >= today:
                next_date = this_year_bday
                turning_age = current_year - birth_date.year
            else:
                next_date = this_year_bday.replace(year=current_year + 1)
                turning_age = current_year + 1 - birth_date.year
                
        elif calendar_type == 'lunar':
            # 农历复杂
            lunar_month = birth_date.month
            lunar_day = birth_date.day
            
            # 1. 尝试将今年的农历生日转为公历
            this_lunar_year_date = BirthdayService._get_solar_date_from_lunar(current_year, lunar_month, lunar_day)
            
            if this_lunar_year_date and this_lunar_year_date >= today:
                next_date = this_lunar_year_date
                turning_age = current_year - birth_date.year
            else:
                # 今年已过，计算明年
                next_date = BirthdayService._get_solar_date_from_lunar(current_year + 1, lunar_month, lunar_day)
                turning_age = current_year + 1 - birth_date.year
        
        if not next_date:
            return None

        days_until = (next_date - today).days
        
        # 修正 1900 默认年份的年龄显示
        if birth_date.year == 1900:
            turning_age = -1 # 表示未知

        return {
            "next_solar_date": next_date,
            "days_until": days_until,
            "age": turning_age,
            "is_today": days_until == 0
        }

    @staticmethod
    def add_reminder(data: BirthdayReminderCreate) -> bool:
        """添加生日提醒"""
        conn = DatabaseService.get_connection()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            sql = """
                INSERT INTO birthday_reminders (name, birth_date, calendar_type, note)
                VALUES (?, ?, ?, ?)
            """
            cursor.execute(sql, (data.name, data.birth_date, data.calendar_type, data.note))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"[Birthday] Add error: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def list_reminders() -> List[dict]:
        """列出所有生日"""
        conn = DatabaseService.get_connection()
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            sql = "SELECT * FROM birthday_reminders WHERE is_active = 1"
            cursor.execute(sql)
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"[Birthday] List error: {e}")
            return []
        finally:
            conn.close()

    @staticmethod
    async def check_and_notify():
        """
        检查所有生日并发送通知 (Core Logic)
        规则: 7天前, 1天前, 当天
        """
        logger.info("[Birthday] Checking reminders...")
        reminders = BirthdayService.list_reminders()
        
        for r in reminders:
            try:
                name = r['name']
                # SQLite 存储为字符串，需转换为 date 对象
                birth_date_str = r['birth_date']
                birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
                
                cal_type = r['calendar_type']
                note = r['note'] or ""
                
                info = BirthdayService.calculate_next_birthday(birth_date, cal_type)
                if not info:
                    continue
                    
                days = info['days_until']
                age = info['age']
                next_date = info['next_solar_date']
                
                # 构造年龄描述
                age_desc = f"{age}岁" if age > 0 else ""
                cal_desc = "农历" if cal_type == 'lunar' else "公历"
                
                msg = ""
                
                if days == 7:
                    msg = f"📅 **生日预告**：\n再过 7 天是 **{name}** 的{age_desc}{cal_desc}生日（{next_date}）。\n📝 备注：{note}\n别忘了准备礼物哦！"
                elif days == 1:
                    msg = f"⏰ **明天是生日**：\n明天就是 **{name}** 的{age_desc}生日啦！\n记得送上祝福！"
                elif days == 0:
                    msg = f"🎂 **生日快乐**：\n今天是 **{name}** 的{age_desc}生日！\n🎉 祝{name}生日快乐，平安喜乐！\n📝 {note}"
                
                if msg:
                    logger.info(f"[Birthday] Sending notification for {name} (days={days})")
                    await _send_rpa_notification(msg)
                    
            except Exception as e:
                # sqlite3.Row 不支持 .get()
                r_name = r['name'] if r else "Unknown"
                logger.error(f"[Birthday] Error checking {r_name}: {e}")
