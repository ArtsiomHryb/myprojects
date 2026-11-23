"""Сервис бэкапа: экспорт дела в ZIP, импорт, проверка локаций."""

from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from case_workspace.documents.models import (
    BackupRecord,
    Document,
    DocumentVersion,
    StorageLocation,
)
from case_workspace.participants.models import Party
from case_workspace.projects.models import Case


class BackupService:
    def __init__(self, session: Session) -> None:
        self.session = session

    # --- проверка локации ---
    def check_location(self, location_id: int) -> tuple[bool, str]:
        loc = self.session.get(StorageLocation, location_id)
        if loc is None:
            return False, "Локация не найдена."
        p = Path(loc.path).expanduser()
        try:
            p.mkdir(parents=True, exist_ok=True)
            test_file = p / ".case_workspace_write_test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
            loc.last_check_at = datetime.utcnow()
            loc.last_check_ok = True
            self.session.commit()
            return True, f"OK: {p}"
        except Exception as exc:  # noqa: BLE001
            loc.last_check_at = datetime.utcnow()
            loc.last_check_ok = False
            self.session.commit()
            return False, f"Ошибка доступа: {exc}"

    def check_all_locations(self) -> list[tuple[int, bool, str]]:
        locs = list(self.session.scalars(select(StorageLocation)))
        results: list[tuple[int, bool, str]] = []
        for l in locs:
            ok, msg = self.check_location(l.id)
            results.append((l.id, ok, msg))
        return results

    # --- экспорт дела в ZIP ---
    def export_case_zip(self, case_id: int, destination: Path) -> Path:
        case = self.session.get(Case, case_id)
        if case is None:
            raise ValueError("Дело не найдено.")

        destination = destination.expanduser()
        if destination.suffix.lower() != ".zip":
            destination = destination.with_suffix(".zip")
        destination.parent.mkdir(parents=True, exist_ok=True)

        manifest = self._build_case_manifest(case)

        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            for doc in self._case_documents(case_id):
                for version in self._document_versions(doc.id):
                    for path_str in (version.file_path, version.pdf_path):
                        if not path_str:
                            continue
                        p = Path(path_str)
                        if p.exists():
                            arc = f"documents/{doc.id}/v{version.version}/{p.name}"
                            zf.write(p, arc)
        return destination

    def _build_case_manifest(self, case: Case) -> dict:
        parties = list(
            self.session.scalars(select(Party).where(Party.case_id == case.id))
        )
        documents = list(
            self.session.scalars(select(Document).where(Document.case_id == case.id))
        )
        return {
            "exported_at": datetime.utcnow().isoformat(),
            "case": {
                "id": case.id,
                "case_number": case.case_number,
                "article": case.article,
                "initiated_at": case.initiated_at.isoformat() if case.initiated_at else "",
                "current_deadline": (
                    case.current_deadline.isoformat() if case.current_deadline else ""
                ),
                "originating_agency": case.originating_agency,
                "location_status": case.location_status.value,
            },
            "parties": [
                {
                    "role": p.role.value,
                    "full_name": p.full_name,
                    "birth_date": p.birth_date.isoformat() if p.birth_date else "",
                    "registration_address": p.registration_address,
                    "residence_address": p.residence_address,
                    "passport_id": p.passport_id,
                    "contact_phone": p.contact_phone,
                }
                for p in parties
            ],
            "documents": [
                {"id": d.id, "title": d.title, "format": d.format, "version": d.version}
                for d in documents
            ],
        }

    def _case_documents(self, case_id: int) -> list[Document]:
        return list(
            self.session.scalars(select(Document).where(Document.case_id == case_id))
        )

    def _document_versions(self, document_id: int) -> list[DocumentVersion]:
        return list(
            self.session.scalars(
                select(DocumentVersion).where(DocumentVersion.document_id == document_id)
            )
        )

    # --- восстановление (импорт) ---
    def inspect_zip(self, zip_path: Path) -> dict:
        if not zip_path.exists():
            raise ValueError("ZIP-файл не найден.")
        with zipfile.ZipFile(zip_path, "r") as zf:
            if "manifest.json" not in zf.namelist():
                raise ValueError("Не найден manifest.json — это не бэкап Case Workspace.")
            manifest = json.loads(zf.read("manifest.json"))
        return manifest

    def restore_case_zip(
        self,
        zip_path: Path,
        restore_documents: bool = True,
    ) -> dict:
        """Восстанавливает дело из ZIP.

        Внимание: создаёт **новое** дело с тем же номером, если оригинал
        уже существует — будет ошибка уникальности. Используйте inspect_zip
        сначала, чтобы убедиться.
        """
        if not zip_path.exists():
            raise ValueError("ZIP-файл не найден.")
        manifest = self.inspect_zip(zip_path)
        case_data = manifest.get("case", {})
        case_number = case_data.get("case_number")
        if not case_number:
            raise ValueError("В манифесте нет номера дела.")

        existing = self.session.scalar(select(Case).where(Case.case_number == case_number))
        if existing is not None:
            raise ValueError(
                f"Дело {case_number} уже существует в системе. "
                f"Удалите его или восстановите под другим номером."
            )

        # Создаём дело
        from datetime import date as date_cls

        new_case = Case(
            case_number=case_number,
            year=case_number[:2],
            sequential_number=case_number[-4:],
            article=case_data.get("article", ""),
            article_code=case_data.get("article", "").split(" ")[0] if case_data.get("article") else "",
            article_part="",
            initiated_at=_parse_date(case_data.get("initiated_at")),
            current_deadline=_parse_date(case_data.get("current_deadline")),
            originating_agency=case_data.get("originating_agency", ""),
            owner_id=1,  # TODO: привязать к текущему админу
        )
        self.session.add(new_case)
        self.session.flush()

        # Участники
        from case_workspace.participants.models import PartyRole

        for p_data in manifest.get("parties", []):
            try:
                role = PartyRole(p_data.get("role", "other"))
            except ValueError:
                role = PartyRole.OTHER
            self.session.add(
                Party(
                    case_id=new_case.id,
                    role=role,
                    full_name=p_data.get("full_name", ""),
                    birth_date=_parse_date(p_data.get("birth_date")),
                    registration_address=p_data.get("registration_address", ""),
                    residence_address=p_data.get("residence_address", ""),
                    passport_id=p_data.get("passport_id", ""),
                    contact_phone=p_data.get("contact_phone", ""),
                )
            )

        self.session.commit()

        return {
            "case_id": new_case.id,
            "case_number": new_case.case_number,
            "parties_restored": len(manifest.get("parties", [])),
            "documents_in_archive": len(manifest.get("documents", [])),
            "restored_files": 0,
            "note": "Документы и файлы не восстанавливались (только манифест).",
        }


def _parse_date(value) -> "date | None":
    from datetime import date as date_cls

    if not value:
        return None
    if isinstance(value, date_cls):
        return value
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        return None
