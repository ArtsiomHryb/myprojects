"""Модели дел, событий, продлений, тегов, заметок."""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from case_workspace.db.models import Base
from case_workspace.utils.time import utc_now


class LocationStatus(str, enum.Enum):
    WITH_ME = "with_me"
    TRANSFERRED = "transferred"
    ARCHIVED = "archived"


class MergeStatus(str, enum.Enum):
    STANDALONE = "standalone"
    MERGED_INTO = "merged_into"
    MERGED_HOLDER = "merged_holder"


class EventType(str, enum.Enum):
    INITIATED = "initiated"
    RESUMED = "resumed"
    TRANSFERRED = "transferred"
    SUSPENDED = "suspended"
    MERGED = "merged"


class Case(Base):
    __tablename__ = "case"

    id: Mapped[int] = mapped_column(primary_key=True)

    case_number: Mapped[str | None] = mapped_column(
        String(11), unique=True, nullable=True, index=True
    )
    year: Mapped[str] = mapped_column(String(2), index=True)
    sequential_number: Mapped[str] = mapped_column(String(4))

    article: Mapped[str] = mapped_column(String(64), default="")
    article_code: Mapped[str] = mapped_column(String(16), default="", index=True)
    article_part: Mapped[str] = mapped_column(String(8), default="")

    initiated_at: Mapped[date] = mapped_column(Date, index=True)
    current_deadline: Mapped[date] = mapped_column(Date, index=True)
    total_period_months: Mapped[int] = mapped_column(Integer, default=2)

    originating_agency: Mapped[str] = mapped_column(String(255), default="")

    location_status: Mapped[LocationStatus] = mapped_column(
        SAEnum(LocationStatus), default=LocationStatus.WITH_ME
    )
    transferred_to: Mapped[str] = mapped_column(String(255), default="")
    transferred_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expected_return_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    color_tag: Mapped[str] = mapped_column(String(16), default="")

    parent_case_id: Mapped[int | None] = mapped_column(
        ForeignKey("case.id"), nullable=True, index=True
    )
    is_episode: Mapped[bool] = mapped_column(Boolean, default=False)

    merge_status: Mapped[MergeStatus] = mapped_column(
        SAEnum(MergeStatus), default=MergeStatus.STANDALONE
    )
    merged_into_case_id: Mapped[int | None] = mapped_column(
        ForeignKey("case.id"), nullable=True
    )

    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resumed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    suspension_reason: Mapped[str] = mapped_column(String(512), default="")

    damage_amount: Mapped[str] = mapped_column(String(32), default="")
    damage_currency: Mapped[str] = mapped_column(String(8), default="BYN")

    owner_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"), index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )

    parties: Mapped[list["Party"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )


    @property
    def accused_name(self) -> str:
        from case_workspace.participants.models import PartyRole

        for p in self.parties:
            if p.role == PartyRole.ACCUSED:
                return p.full_name
        return ""

    @property
    def victim_name(self) -> str:
        from case_workspace.participants.models import PartyRole

        for p in self.parties:
            if p.role == PartyRole.VICTIM:
                return p.full_name
        return ""


class CaseEvent(Base):
    __tablename__ = "case_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), index=True)
    type: Mapped[EventType] = mapped_column(SAEnum(EventType))
    date: Mapped[date] = mapped_column(Date)
    to_address: Mapped[str] = mapped_column(String(255), default="")
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class DeadlineExtension(Base):
    __tablename__ = "deadline_extension"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), index=True)
    old_deadline: Mapped[date] = mapped_column(Date)
    new_deadline: Mapped[date] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class Tag(Base):
    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    color: Mapped[str] = mapped_column(String(16), default="#4F46E5")


class CaseTag(Base):
    __tablename__ = "case_tag"

    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), primary_key=True)


class Note(Base):
    __tablename__ = "note"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )

class CaseDesktopPosition(Base):
    __tablename__ = "case_desktop_position"

    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), primary_key=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, index=True)
