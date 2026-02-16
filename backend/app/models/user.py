from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from typing import List


class UserCreate(BaseModel):
    email: EmailStr
    timezone: str = Field(default="UTC", description="IANA timezone")
    cf_handle: str | None = None
    cf_api_key: str | None = None
    cf_api_secret: str | None = None
    reminder_count: int = Field(default=3, ge=1, le=10)
    reminder_start_minutes: int = Field(default=30, ge=0, le=240)
    reminder_interval_minutes: int = Field(default=10, ge=1, le=120)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    timezone: str
    cf_handle: str | None
    reminder_count: int
    reminder_start_minutes: int
    reminder_interval_minutes: int
    created_at: datetime

    class Config:
        from_attributes = True


class ContestSubscriptionCreate(BaseModel):
    contest_ids: List[int]


class ContestSubscriptionOut(BaseModel):
    contest_id: int
    contest_name: str
    start_time_utc: datetime | None

    class Config:
        from_attributes = True


class NotificationPreview(BaseModel):
    contest_id: int
    contest_name: str
    start_time_utc: datetime | None
    reminders_utc: List[datetime]
    reminders_local_formatted: List[str]


class NotificationDispatchResponse(BaseModel):
    sent_count: int
    errors: List[str]
