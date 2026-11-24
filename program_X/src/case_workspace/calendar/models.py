"""Модели календаря."""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from case_workspace.db.models import Base


class EventType(str, enum.Enum):
    DEADLINE = "deadline"
    REMINDER = "reminder"
    MEETING = "meeting"
    OTHER = "other"

    @property
    def label(self) -> str:
        return {
            EventType.DEADLINE: "Дедлайн",
            EventType.REMINDER: "Напоминание",
            EventType.MEETING: "Встреча",
            EventType.OTHER: "Иное",
        }[self]


class CalendarEvent(Base):
    __tablename__ = "calendar_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int | None] = mapped_column(
        ForeignKey("case.id"), nullable=True, index=True
    )

    event_date: Mapped[date] = mapped_column(Date, index=True)
    type: Mapped[EventType] = mapped_column(SAEnum(EventType), default=EventType.REMINDER)
    title: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    done: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
