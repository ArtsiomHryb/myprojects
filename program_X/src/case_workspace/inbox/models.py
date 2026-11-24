"""Модели «Неразобранного» (Inbox)."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from case_workspace.db.models import Base


class InboxSource(str, enum.Enum):
    PROGRAM = "program"
    FILE = "file"
    CLIPBOARD = "clipboard"
    BOT = "bot"

    @property
    def label(self) -> str:
        return {
            InboxSource.PROGRAM: "Программа",
            InboxSource.FILE: "Файл",
            InboxSource.CLIPBOARD: "Буфер обмена",
            InboxSource.BOT: "Telegram-бот",
        }[self]


class InboxStatus(str, enum.Enum):
    NEW = "new"
    REVIEWED = "reviewed"
    ATTACHED = "attached"
    IGNORED = "ignored"

    @property
    def label(self) -> str:
        return {
            InboxStatus.NEW: "Новое",
            InboxStatus.REVIEWED: "Проверено",
            InboxStatus.ATTACHED: "Привязано",
            InboxStatus.IGNORED: "Игнорировано",
        }[self]


class InboxItem(Base):
    __tablename__ = "inbox_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[InboxSource] = mapped_column(
        SAEnum(InboxSource), default=InboxSource.FILE
    )
    source_file: Mapped[str] = mapped_column(String(512), default="")
    received_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    raw_text: Mapped[str] = mapped_column(Text, default="")
    extract_method: Mapped[str] = mapped_column(String(64), default="")

    extracted_json: Mapped[str] = mapped_column(Text, default="")
    hypotheses_json: Mapped[str] = mapped_column(Text, default="")
    auto_tags: Mapped[str] = mapped_column(String(512), default="")

    status: Mapped[InboxStatus] = mapped_column(
        SAEnum(InboxStatus), default=InboxStatus.NEW
    )
    attached_to_case_id: Mapped[int | None] = mapped_column(
        ForeignKey("case.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
