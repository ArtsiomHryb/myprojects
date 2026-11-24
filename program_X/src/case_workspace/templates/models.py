"""Модели шаблонов (бланков)."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from case_workspace.db.models import Base


class TemplateCategory(str, enum.Enum):
    BANKS = "banks"
    MOBILE = "mobile"
    GOVERNMENT = "government"
    OPERATIONS = "operations"
    PROTOCOLS = "protocols"
    OTHER = "other"

    @property
    def label(self) -> str:
        return {
            TemplateCategory.BANKS: "Банки",
            TemplateCategory.MOBILE: "Сотовые операторы",
            TemplateCategory.GOVERNMENT: "Госорганы",
            TemplateCategory.OPERATIONS: "Постановления",
            TemplateCategory.PROTOCOLS: "Протоколы",
            TemplateCategory.OTHER: "Иное",
        }[self]


class Template(Base):
    __tablename__ = "template"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    category: Mapped[TemplateCategory] = mapped_column(
        SAEnum(TemplateCategory), default=TemplateCategory.OTHER
    )
    subcategory: Mapped[str] = mapped_column(String(128), default="")
    tags: Mapped[str] = mapped_column(String(512), default="")
    source_path: Mapped[str] = mapped_column(String(512))
    fields_schema: Mapped[str] = mapped_column(Text, default="")  # JSON
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    comment: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
