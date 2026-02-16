from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import AWS_SES_REGION, AWS_SES_SENDER
from app.db.models import ContestSubscription, NotificationLog, User


def build_reminder_schedule(
    start_time_utc: datetime | None,
    reminder_count: int,
    start_minutes_before: int,
    interval_minutes: int,
) -> List[datetime]:
    if start_time_utc is None:
        return []

    first_reminder = start_time_utc - timedelta(minutes=start_minutes_before)
    return [first_reminder + timedelta(minutes=interval_minutes * i) for i in range(reminder_count)]


def format_local_times(times: List[datetime], timezone_name: str) -> List[str]:
    try:
        from zoneinfo import ZoneInfo
    except Exception:
        return []

    formatted: List[str] = []
    zone = ZoneInfo(timezone_name)
    for dt in times:
        formatted.append(dt.astimezone(zone).strftime("%Y-%m-%d %I:%M %p"))
    return formatted


def get_ses_client():
    return boto3.client("ses", region_name=AWS_SES_REGION)


def build_email_body(user: User, subscription: ContestSubscription, reminders_local: List[str]) -> str:
    lines = [
        f"Hi {user.cf_handle or 'Codeforces user'},",
        "",
        f"Contest: {subscription.contest_name} (ID: {subscription.contest_id})",
        f"Start (UTC): {subscription.start_time_utc}",
        "Scheduled reminders (local time):",
    ]
    lines.extend(f"- {t}" for t in reminders_local)
    lines.append("\nYou received this because you subscribed to this contest.")
    return "\n".join(lines)


def send_email_notification(user: User, subscription: ContestSubscription, reminders_local: List[str]) -> None:
    if not AWS_SES_SENDER:
        raise RuntimeError("AWS_SES_SENDER is not configured")

    ses = get_ses_client()
    body = build_email_body(user, subscription, reminders_local)
    try:
        ses.send_email(
            Source=AWS_SES_SENDER,
            Destination={"ToAddresses": [user.email]},
            Message={
                "Subject": {"Data": f"Codeforces contest reminder: {subscription.contest_name}"},
                "Body": {"Text": {"Data": body}},
            },
        )
    except (ClientError, BotoCoreError) as exc:
        raise RuntimeError(f"SES send failed: {exc}") from exc


def is_due(reminder_time: datetime, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    return reminder_time <= now


async def mark_sent(session, subscription_id: int, reminder_time: datetime) -> None:
    session.add(NotificationLog(subscription_id=subscription_id, send_time=reminder_time))
    await session.commit()


async def already_sent(session, subscription_id: int, reminder_time: datetime) -> bool:
    result = await session.execute(
        NotificationLog.__table__.select()
        .where(NotificationLog.subscription_id == subscription_id)
        .where(NotificationLog.send_time == reminder_time)
    )
    return result.first() is not None
