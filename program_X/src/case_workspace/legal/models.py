"""Модели правовой справки (статьи УК РБ)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from case_workspace.db.models import Base
from case_workspace.utils.time import utc_now


class UkArticleCache(Base):
    __tablename__ = "uk_article_cache"
    __table_args__ = (
        UniqueConstraint("code", "part", name="uq_uk_article"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), index=True)
    part: Mapped[str] = mapped_column(String(8), default="")

    text: Mapped[str] = mapped_column(Text, default="")
    comment: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str] = mapped_column(String(1024), default="")

    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )
