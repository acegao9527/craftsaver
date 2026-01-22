from pydantic import BaseModel, Field
from datetime import date
from typing import Optional

class BirthdayReminderCreate(BaseModel):
    name: str = Field(..., description="姓名")
    birth_date: date = Field(..., description="生日 (YYYY-MM-DD), 年份未知填1900")
    calendar_type: str = Field("solar", description="solar(公历) 或 lunar(农历)")
    note: Optional[str] = Field(None, description="备注")

class BirthdayReminder(BirthdayReminderCreate):
    id: int
    is_active: bool
    created_at: Optional[str] = None # For display

    class Config:
        from_attributes = True
