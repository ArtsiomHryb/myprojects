"""Модель участника дела."""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from case_workspace.db.models import Base
from case_workspace.utils.time import utc_now


class PartyRole(str, enum.Enum):
    ACCUSED = "accused"
    VICTIM = "victim"
    WITNESS = "witness"
    OTHER = "other"

    @property
    def label(self) -> str:
        return {
            PartyRole.ACCUSED: "Обвиняемый",
            PartyRole.VICTIM: "Потерпевший",
            PartyRole.WITNESS: "Свидетель",
            PartyRole.OTHER: "Иное",
        }[self]


class Party(Base):
    __tablename__ = "party"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), index=True)

    role: Mapped[PartyRole] = mapped_column(SAEnum(PartyRole), default=PartyRole.ACCUSED)
    full_name: Mapped[str] = mapped_column(String(255))
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    registration_address: Mapped[str] = mapped_column(String(512), default="")
    residence_address: Mapped[str] = mapped_column(String(512), default="")
    passport_id: Mapped[str] = mapped_column(String(32), default="")
    contact_phone: Mapped[str] = mapped_column(String(32), default="")
    comment: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )

    case: Mapped["Case"] = relationship(back_populates="parties")