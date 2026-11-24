"""Модели документов, версий, локаций хранения, записей бэкапа."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from case_workspace.db.models import Base


class DocumentType(str, enum.Enum):
    GENERATED = "generated"
    ATTACHED = "attached"


class DocumentStatus(str, enum.Enum):
    DRAFT = "draft"
    SENDING = "sending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    ARCHIVED = "archived"

    @property
    def label(self) -> str:
        return {
            DocumentStatus.DRAFT: "Черновик",
            DocumentStatus.SENDING: "На отправке",
            DocumentStatus.IN_PROGRESS: "На исполнении",
            DocumentStatus.DONE: "Исполнено",
            DocumentStatus.ARCHIVED: "В архиве",
        }[self]


class Document(Base):
    __tablename__ = "document"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), index=True)
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("template.id"), nullable=True
    )
    party_id: Mapped[int | None] = mapped_column(
        ForeignKey("party.id"), nullable=True
    )

    doc_type: Mapped[DocumentType] = mapped_column(
        SAEnum(DocumentType), default=DocumentType.GENERATED
    )
    title: Mapped[str] = mapped_column(String(255), default="")
    data_json: Mapped[str] = mapped_column(Text, default="")  # снимок данных
    format: Mapped[str] = mapped_column(String(16), default="docx")
    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(DocumentStatus), default=DocumentStatus.DRAFT
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    edited_manually: Mapped[bool] = mapped_column(Boolean, default=False)
    file_paths: Mapped[str] = mapped_column(Text, default="")  # JSON

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    rendered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    saved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    printed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class DocumentVersion(Base):
    __tablename__ = "document_version"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    file_path: Mapped[str] = mapped_column(String(1024))
    pdf_path: Mapped[str] = mapped_column(String(1024), default="")
    change_reason: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class StorageLocation(Base):
    __tablename__ = "storage_location"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(64), default="")
    path: Mapped[str] = mapped_column(String(1024))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_check_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_check_ok: Mapped[bool] = mapped_column(Boolean, default=False)


class BackupRecord(Base):
    __tablename__ = "backup_record"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("document.id"), nullable=True, index=True
    )
    location_id: Mapped[int | None] = mapped_column(
        ForeignKey("storage_location.id"), nullable=True
    )
    file_name: Mapped[str] = mapped_column(String(255), default="")
    destination: Mapped[str] = mapped_column(String(1024), default="")
    at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    ok: Mapped[bool] = mapped_column(Boolean, default=False)
    size: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String(64), default="")
    error: Mapped[str] = mapped_column(String(512), default="")
