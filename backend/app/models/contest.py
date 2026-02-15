from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class Contest(BaseModel):
    id: int
    name: str
    phase: str
    start_time_utc: datetime | None
    duration_seconds: int | None
    relative_time_seconds: int | None


class AuthParams(BaseModel):
    api_key: str
    api_secret: str
