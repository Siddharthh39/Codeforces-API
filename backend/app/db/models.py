from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    cf_handle: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cf_api_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    cf_api_secret: Mapped[str | None] = mapped_column(String(256), nullable=True)
    reminder_count: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    reminder_start_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    reminder_interval_minutes: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    subscriptions: Mapped[list["ContestSubscription"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class ContestSubscription(Base):
    __tablename__ = "contest_subscriptions"
    __table_args__ = (UniqueConstraint("user_id", "contest_id", name="uq_user_contest"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    contest_id: Mapped[int] = mapped_column(Integer, nullable=False)
    contest_name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_time_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="subscriptions")
    notifications: Mapped[list["NotificationLog"]] = relationship(
        back_populates="subscription", cascade="all, delete-orphan"
    )


class NotificationLog(Base):
    __tablename__ = "notification_logs"
    __table_args__ = (UniqueConstraint("subscription_id", "send_time", name="uq_notification_once"),)

    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("contest_subscriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    send_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    subscription: Mapped[ContestSubscription] = relationship(back_populates="notifications")
