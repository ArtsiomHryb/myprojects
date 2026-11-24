"""Модели идентификаторов."""

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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from case_workspace.db.models import Base


class IdentifierType(str, enum.Enum):
    CARD = "card"
    IBAN = "iban"
    PHONE = "phone"
    IP = "ip"
    OTHER = "other"

    @property
    def label(self) -> str:
        return {
            IdentifierType.CARD: "Банковская карта",
            IdentifierType.IBAN: "Банковский счёт (IBAN)",
            IdentifierType.PHONE: "Абонентский номер",
            IdentifierType.IP: "IP-адрес",
            IdentifierType.OTHER: "Иное",
        }[self]


class VerificationStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    PARTIAL = "partial"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"

    @property
    def label(self) -> str:
        return {
            VerificationStatus.CONFIRMED: "подтверждено",
            VerificationStatus.PARTIAL: "частично",
            VerificationStatus.CONFLICT: "расхождение",
            VerificationStatus.UNKNOWN: "неизвестно",
        }[self]


class Identifier(Base):
    __tablename__ = "identifier"
    __table_args__ = (
        UniqueConstraint("case_id", "type", "normalized_value", name="uq_case_identifier"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), index=True)
    party_id: Mapped[int | None] = mapped_column(
        ForeignKey("party.id"), nullable=True, index=True
    )

    type: Mapped[IdentifierType] = mapped_column(SAEnum(IdentifierType))
    value: Mapped[str] = mapped_column(String(128))
    normalized_value: Mapped[str] = mapped_column(String(128), index=True)

    resolved_local: Mapped[str] = mapped_column(Text, default="")
    resolved_online: Mapped[str] = mapped_column(Text, default="")
    verification_status: Mapped[VerificationStatus] = mapped_column(
        SAEnum(VerificationStatus), default=VerificationStatus.UNKNOWN
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    comment: Mapped[str] = mapped_column(String(512), default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class ResolverCache(Base):
    __tablename__ = "resolver_cache"
    __table_args__ = (
        UniqueConstraint("type", "normalized_value", "source", name="uq_resolver_cache"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[IdentifierType] = mapped_column(SAEnum(IdentifierType))
    normalized_value: Mapped[str] = mapped_column(String(128), index=True)
    source: Mapped[str] = mapped_column(String(32))
    result_json: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    ttl_days: Mapped[int] = mapped_column(Integer, default=30)


class BankCode(Base):
    __tablename__ = "bank_code"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    bank_name: Mapped[str] = mapped_column(String(255))
    bic: Mapped[str] = mapped_column(String(16), default="")
    country: Mapped[str] = mapped_column(String(4), default="BY")


class BinRange(Base):
    __tablename__ = "bin_range"

    id: Mapped[int] = mapped_column(primary_key=True)
    bin_start: Mapped[str] = mapped_column(String(8), index=True)
    bin_end: Mapped[str] = mapped_column(String(8), default="")
    scheme: Mapped[str] = mapped_column(String(32), default="")
    card_type: Mapped[str] = mapped_column(String(32), default="")
    bank_name: Mapped[str] = mapped_column(String(255), default="")
    country: Mapped[str] = mapped_column(String(4), default="")
