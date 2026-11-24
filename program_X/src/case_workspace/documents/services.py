"""Сервис рендеринга документов."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import date, datetime
from pathlib import Path

from docxtpl import DocxTemplate
from sqlalchemy import select
from sqlalchemy.orm import Session

from case_workspace.config import DATA_DIR
from case_workspace.db.models import UserAccount
from case_workspace.documents.models import (
    BackupRecord,
    Document,
    DocumentStatus,
    DocumentType,
    DocumentVersion,
    StorageLocation,
)
from case_workspace.participants.models import Party, PartyRole
from case_workspace.projects.models import Case
from case_workspace.templates.models import Template
from case_workspace.templates.service import TemplateService
from case_workspace.utils.time import utc_now

MONTHS_RU = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


def _fmt_date(d: date | None) -> str:
    if d is None:
        return ""
    return d.strftime("%d.%m.%Y")


def _fmt_date_long(d: date | None) -> str:
    if d is None:
        return ""
    return f"{d.day} {MONTHS_RU[d.month - 1]} {d.year} г."


def _set_nested(ctx: dict, dotted: str, value) -> None:
    parts = dotted.split(".")
    node = ctx
    for p in parts[:-1]:
        if p not in node or not isinstance(node[p], dict):
            node[p] = {}
        node = node[p]
    node[parts[-1]] = value


def _party_ctx(p: Party | None) -> dict | None:
    if p is None:
        return None
    return {
        "full_name": p.full_name,
        "birth_date": _fmt_date(p.birth_date),
        "registration_address": p.registration_address,
        "residence_address": p.residence_address,
        "passport_id": p.passport_id,
        "contact_phone": p.contact_phone,
        "role": p.role.label,
    }


class DocumentService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.templates = TemplateService(session)

    # --- каскад данных ---
    def build_context(
        self,
        case_id: int,
        party_id: int | None = None,
        extra_data: dict | None = None,
    ) -> dict:
        case = self.session.get(Case, case_id)
        if case is None:
            raise ValueError("Дело не найдено.")

        profile_user = self.session.scalar(
            select(UserAccount)
            .where(UserAccount.role == UserAccount.__table__.c.role.type.enum_class.ADMIN)
            .order_by(UserAccount.id)
            .limit(1)
        ) or self.session.scalar(select(UserAccount).order_by(UserAccount.id).limit(1))

        parties = list(
            self.session.scalars(select(Party).where(Party.case_id == case_id))
        )
        accused_list = [p for p in parties if p.role == PartyRole.ACCUSED]
        victim_list = [p for p in parties if p.role == PartyRole.VICTIM]

        selected_party: Party | None = None
        if party_id is not None:
            selected_party = next((p for p in parties if p.id == party_id), None)
        if selected_party is None:
            selected_party = accused_list[0] if accused_list else (
                victim_list[0] if victim_list else None
            )

        accused = accused_list[0] if accused_list else None
        victim = victim_list[0] if victim_list else None

        today = date.today()
        ctx = {
            "case": {
                "case_number": case.case_number or "",
                "article": case.article or "",
                "article_code": case.article_code or "",
                "article_part": case.article_part or "",
                "initiated_at": _fmt_date(case.initiated_at),
                "current_deadline": _fmt_date(case.current_deadline),
                "originating_agency": case.originating_agency or "",
            },
            "profile": {
                "full_name": profile_user.full_name if profile_user else "",
                "position": profile_user.position if profile_user else "",
                "rank": profile_user.rank if profile_user else "",
                "organization_name": profile_user.organization_name if profile_user else "",
            },
            "accused": _party_ctx(accused) or {},
            "victim": _party_ctx(victim) or {},
            "party": _party_ctx(selected_party) or {},
            "accused_list": [p for p in (_party_ctx(p) for p in accused_list) if p],
            "victim_list": [p for p in (_party_ctx(p) for p in victim_list) if p],
            "current_date": _fmt_date(today),
            "current_date_long": _fmt_date_long(today),
        }

        if extra_data:
            for key, value in extra_data.items():
                if "." in key:
                    _set_nested(ctx, key, value)
                else:
                    ctx[key] = value

        return ctx

    # --- рендеринг ---
    def render(
        self,
        template_id: int,
        case_id: int,
        party_id: int | None = None,
        extra_data: dict | None = None,
        convert_to_pdf: bool = True,
    ) -> Document:
        template = self.templates.get(template_id)
        if template is None:
            raise ValueError("Шаблон не найден.")
        if not Path(template.source_path).exists():
            raise ValueError(f"Файл шаблона не найден: {template.source_path}")

        context = self.build_context(case_id, party_id, extra_data)

        doc = Document(
            case_id=case_id,
            template_id=template_id,
            party_id=party_id,
            doc_type=DocumentType.GENERATED,
            title=template.name,
            data_json=json.dumps(context, ensure_ascii=False, default=str),
            format="docx",
            status=DocumentStatus.DRAFT,
            version=1,
        )
        self.session.add(doc)
        self.session.flush()

        out_dir = self._doc_dir(case_id, doc.id)
        out_dir.mkdir(parents=True, exist_ok=True)
        docx_path = out_dir / f"v1.docx"

        tpl = DocxTemplate(template.source_path)
        tpl.render(context, autoescape=True)
        tpl.save(str(docx_path))

        pdf_path: Path | None = None
        if convert_to_pdf:
            pdf_path = self._convert_to_pdf(docx_path)

        version = DocumentVersion(
            document_id=doc.id,
            version=1,
            file_path=str(docx_path),
            pdf_path=str(pdf_path) if pdf_path else "",
            change_reason="первое формирование",
        )
        self.session.add(version)

        doc.file_paths = json.dumps(
            {
                "local_docx": str(docx_path),
                "local_pdf": str(pdf_path) if pdf_path else "",
            },
            ensure_ascii=False,
        )
        doc.rendered_at = utc_now()
        doc.saved_at = utc_now()

        self._backup_to_locations(doc, docx_path)
        if pdf_path:
            self._backup_to_locations(doc, pdf_path)

        self.session.commit()
        return doc

    def _doc_dir(self, case_id: int, doc_id: int) -> Path:
        case = self.session.get(Case, case_id)
        if case and case.case_number:
            sub = case.case_number
        else:
            sub = f"case_{case_id}"
        return DATA_DIR / "documents" / sub

    def _convert_to_pdf(self, docx_path: Path) -> Path | None:
        try:
            from docx2pdf import convert  # noqa: PLC0415

            pdf_path = docx_path.with_suffix(".pdf")
            convert(str(docx_path), str(pdf_path))
            return pdf_path if pdf_path.exists() else None
        except Exception:  # noqa: BLE001
            return None

    def _backup_to_locations(self, doc: Document, src: Path) -> None:
        if not src.exists():
            return
        locations = list(
            self.session.scalars(
                select(StorageLocation).where(StorageLocation.enabled == True)  # noqa: E712
            )
        )
        for loc in locations:
            try:
                dest_dir = Path(loc.path)
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = dest_dir / src.name
                shutil.copy2(src, dest)
                sha = hashlib.sha256(src.read_bytes()).hexdigest()
                self.session.add(
                    BackupRecord(
                        document_id=doc.id,
                        location_id=loc.id,
                        file_name=src.name,
                        destination=str(dest),
                        ok=True,
                        size=src.stat().st_size,
                        sha256=sha,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                self.session.add(
                    BackupRecord(
                        document_id=doc.id,
                        location_id=loc.id,
                        file_name=src.name,
                        destination=str(Path(loc.path) / src.name),
                        ok=False,
                        error=str(exc)[:500],
                    )
                )

    # --- CRUD ---
    def list_documents(self, case_id: int) -> list[Document]:
        return list(
            self.session.scalars(
                select(Document)
                .where(Document.case_id == case_id)
                .order_by(Document.created_at.desc())
            )
        )

    def get(self, document_id: int) -> Document | None:
        return self.session.get(Document, document_id)

    def list_versions(self, document_id: int) -> list[DocumentVersion]:
        return list(
            self.session.scalars(
                select(DocumentVersion)
                .where(DocumentVersion.document_id == document_id)
                .order_by(DocumentVersion.version)
            )
        )

    def delete(self, document_id: int) -> None:
        doc = self.session.get(Document, document_id)
        if doc is None:
            return
        versions = list(
            self.session.scalars(
                select(DocumentVersion).where(DocumentVersion.document_id == document_id)
            )
        )
        for v in versions:
            for p in (v.file_path, v.pdf_path):
                if p and Path(p).exists():
                    try:
                        Path(p).unlink()
                    except OSError:
                        pass
            self.session.delete(v)
        self.session.delete(doc)
        self.session.commit()


# ===== Storage locations =====
def add_storage_location(
    session: Session, label: str, path: str, enabled: bool = True
) -> StorageLocation:
    p = Path(path).expanduser()
    ok = p.exists() or p.parent.exists()
    loc = StorageLocation(label=label, path=str(p), enabled=enabled, last_check_ok=ok)
    session.add(loc)
    session.commit()
    return loc


def list_storage_locations(session: Session) -> list[StorageLocation]:
    return list(session.scalars(select(StorageLocation).order_by(StorageLocation.id)))


def delete_storage_location(session: Session, location_id: int) -> None:
    loc = session.get(StorageLocation, location_id)
    if loc:
        session.delete(loc)
        session.commit()
