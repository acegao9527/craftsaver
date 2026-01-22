from fastapi import APIRouter
from src.birthday_reminder.models import BirthdayReminderCreate
from src.birthday_reminder.service import BirthdayService

router = APIRouter(prefix="/birthday", tags=["Birthday Reminder"])

@router.post("/add")
async def add_birthday(data: BirthdayReminderCreate):
    success = BirthdayService.add_reminder(data)
    if success:
        return {"status": "success", "message": "Birthday reminder added."}
    return {"status": "error", "message": "Failed to add reminder."}

@router.get("/list")
async def list_birthdays():
    return BirthdayService.list_reminders()

@router.post("/test_check")
async def test_check():
    """手动触发一次检查"""
    await BirthdayService.check_and_notify()
    return {"status": "success", "message": "Check triggered."}
