from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.db.models import ContestSubscription, User
from app.models.contest import Contest
from app.models.user import (
    ContestSubscriptionCreate,
    ContestSubscriptionOut,
    NotificationDispatchResponse,
    NotificationPreview,
    UserCreate,
    UserOut,
)
from app.services.codeforces import CodeforcesService
from app.services.notifications import (
    already_sent,
    build_reminder_schedule,
    format_local_times,
    is_due,
    mark_sent,
    send_email_notification,
)

router = APIRouter(prefix="/users", tags=["users"])
service = CodeforcesService()


@router.post("", response_model=UserOut)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> UserOut:
    user = User(
        email=payload.email,
        timezone=payload.timezone,
        cf_handle=payload.cf_handle,
        cf_api_key=payload.cf_api_key,
        cf_api_secret=payload.cf_api_secret,
        reminder_count=payload.reminder_count,
        reminder_start_minutes=payload.reminder_start_minutes,
        reminder_interval_minutes=payload.reminder_interval_minutes,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)) -> UserOut:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/{user_id}/subscriptions", response_model=List[ContestSubscriptionOut])
async def save_subscriptions(
    user_id: int,
    payload: ContestSubscriptionCreate,
    db: AsyncSession = Depends(get_db),
) -> List[ContestSubscriptionOut]:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not payload.contest_ids:
        raise HTTPException(status_code=400, detail="contest_ids cannot be empty")

    # Fetch upcoming contests and map by id for validation
    upcoming: List[Contest] = await service.get_upcoming_contests(auth=None)
    upcoming_by_id = {c.id: c for c in upcoming}

    # Remove existing subscriptions for contests not in new list
    await db.execute(
        delete(ContestSubscription).where(
            ContestSubscription.user_id == user_id,
            ~ContestSubscription.contest_id.in_(payload.contest_ids),
        )
    )

    saved: List[ContestSubscription] = []
    for contest_id in payload.contest_ids:
        contest = upcoming_by_id.get(contest_id)
        if not contest:
            raise HTTPException(status_code=400, detail=f"Contest {contest_id} is not upcoming or not found")

        existing = await db.execute(
            select(ContestSubscription).where(
                ContestSubscription.user_id == user_id,
                ContestSubscription.contest_id == contest_id,
            )
        )
        existing_obj = existing.scalar_one_or_none()
        if existing_obj:
            existing_obj.contest_name = contest.name
            existing_obj.start_time_utc = contest.start_time_utc
            saved.append(existing_obj)
            continue

        sub = ContestSubscription(
            user_id=user_id,
            contest_id=contest_id,
            contest_name=contest.name,
            start_time_utc=contest.start_time_utc,
        )
        db.add(sub)
        saved.append(sub)

    await db.commit()
    for sub in saved:
        await db.refresh(sub)
    return saved


@router.get("/{user_id}/subscriptions", response_model=List[ContestSubscriptionOut])
async def list_subscriptions(user_id: int, db: AsyncSession = Depends(get_db)) -> List[ContestSubscriptionOut]:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(select(ContestSubscription).where(ContestSubscription.user_id == user_id))
    return list(result.scalars())


@router.get("/{user_id}/notification-preview", response_model=List[NotificationPreview])
async def preview_notifications(user_id: int, db: AsyncSession = Depends(get_db)) -> List[NotificationPreview]:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(select(ContestSubscription).where(ContestSubscription.user_id == user_id))
    subs = list(result.scalars())

    previews: List[NotificationPreview] = []
    for sub in subs:
        reminders = build_reminder_schedule(
            sub.start_time_utc,
            user.reminder_count,
            user.reminder_start_minutes,
            user.reminder_interval_minutes,
        )
        previews.append(
            NotificationPreview(
                contest_id=sub.contest_id,
                contest_name=sub.contest_name,
                start_time_utc=sub.start_time_utc,
                reminders_utc=reminders,
                reminders_local_formatted=format_local_times(reminders, user.timezone),
            )
        )
    return previews


@router.post("/{user_id}/notifications/dispatch", response_model=NotificationDispatchResponse)
async def dispatch_notifications(user_id: int, db: AsyncSession = Depends(get_db)) -> NotificationDispatchResponse:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(select(ContestSubscription).where(ContestSubscription.user_id == user_id))
    subs = list(result.scalars())
    sent_count = 0
    errors: List[str] = []
    now = datetime.now(timezone.utc)

    for sub in subs:
        schedule = build_reminder_schedule(
            sub.start_time_utc,
            user.reminder_count,
            user.reminder_start_minutes,
            user.reminder_interval_minutes,
        )

        for reminder_time in schedule:
            if not is_due(reminder_time, now):
                continue
            if await already_sent(db, sub.id, reminder_time):
                continue

            try:
                send_email_notification(
                    user,
                    sub,
                    format_local_times([reminder_time], user.timezone),
                )
            except Exception as exc:  # noqa: WPS429 - want to capture SES failures
                errors.append(str(exc))
                continue

            await mark_sent(db, sub.id, reminder_time)
            sent_count += 1

    return NotificationDispatchResponse(sent_count=sent_count, errors=errors)
