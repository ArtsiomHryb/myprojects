"""Модели учёта времени (тайминг)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from case_workspace.db.models import Base


class TimeEntry(Base):
    __tablename__ = "time_entry"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), index=True)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("document.id"), nullable=True
    )

    is_running: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    accumulated_seconds: Mapped[int] = mapped_column(Integer, default=0)
    manual_override: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(String(255), default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    @property
    def total_seconds(self) -> int:
        from datetime import datetime as dt

        total = self.accumulated_seconds
        if self.is_running and self.started_at:
            total += int((dt.utcnow() - self.started_at).total_seconds())
        return max(0, total)
