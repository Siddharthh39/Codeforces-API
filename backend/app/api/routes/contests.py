from __future__ import annotations

from datetime import datetime
from typing import List
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies.auth import parse_auth
from app.models.contest import AuthParams, Contest
from app.services.codeforces import CodeforcesService

router = APIRouter(prefix="/contests", tags=["contests"])
service = CodeforcesService()


@router.get("", response_model=List[Contest])
async def list_contests(
    timezone: str | None = Query(default=None, description="IANA timezone like Europe/Berlin"),
    auth: AuthParams | None = Depends(parse_auth),
) -> List[Contest]:
    contests = await service.get_upcoming_contests(auth)
    return _apply_timezone(contests, timezone)


def _apply_timezone(contests: List[Contest], timezone_name: str | None) -> List[Contest]:
    if not timezone_name:
        return contests

    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=400, detail="Invalid timezone identifier") from exc

    converted: List[Contest] = []
    for contest in contests:
        local_start = contest.start_time_utc.astimezone(zone) if contest.start_time_utc else None
        converted.append(
            contest.model_copy(
                update={
                    "start_time_local": local_start,
                    "local_timezone": timezone_name,
                    "start_time_local_formatted": _format_am_pm(local_start),
                }
            )
        )

    return converted


def _format_am_pm(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    # Example: 2026-02-16 03:45 PM
    return dt.strftime("%Y-%m-%d %I:%M %p")
