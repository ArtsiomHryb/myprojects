"""Модели для API и бота: Session, Notification, Blacklist."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from case_workspace.db.models import Base


class SessionToken(Base):
    __tablename__ = "session_token"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, index=True)
    username: Mapped[str] = mapped_column(String(128), default="")
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(16), default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class NotificationType(str, enum.Enum):
    SECURITY = "security"
    AUDIT = "audit"
    ERROR = "error"
    SYSTEM = "system"
    DEADLINE = "deadline"

    @property
    def label(self) -> str:
        return {
            NotificationType.SECURITY: "Безопасность",
            NotificationType.AUDIT: "Аудит",
            NotificationType.ERROR: "Ошибка",
            NotificationType.SYSTEM: "Система",
            NotificationType.DEADLINE: "Срок",
        }[self]


class Severity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Notification(Base):
    __tablename__ = "notification"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[NotificationType] = mapped_column(SAEnum(NotificationType))
    severity: Mapped[Severity] = mapped_column(SAEnum(Severity), default=Severity.INFO)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(32), default="program")
    metadata_json: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TelegramBlacklist(Base):
    __tablename__ = "telegram_blacklist"

    telegram_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(128), default="")
    reason: Mapped[str] = mapped_column(String(512), default="")
    blocked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    blocked_by: Mapped[str] = mapped_column(String(16), default="auto")  # auto/admin
