"""Парсинг плейсхолдеров и нормализация runs в DOCX."""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document as DocxDocument
from docx.document import Document as DocxDocType
from docx.text.paragraph import Paragraph

PLACEHOLDER_RE = re.compile(r"\{\{\s*([\w\.]+)\s*\}\}")


def _iter_paragraphs(doc: DocxDocType):
    for para in doc.paragraphs:
        yield para
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    yield para
    for section in doc.sections:
        for header in (section.header, section.footer):
            if header is None:
                continue
            for para in header.paragraphs:
                yield para


def extract_placeholders(docx_path: Path) -> list[str]:
    """Возвращает список имён плейсхолдеров (без фигурных скобок)."""
    doc = DocxDocument(str(docx_path))
    found: list[str] = []
    seen: set[str] = set()
    for para in _iter_paragraphs(doc):
        text = "".join(run.text for run in para.runs)
        for match in PLACEHOLDER_RE.finditer(text):
            name = match.group(1)
            if name not in seen:
                seen.add(name)
                found.append(name)
    return found


def _paragraph_text(para: Paragraph) -> str:
    return "".join(run.text for run in para.runs)


def _normalize_paragraph(para: Paragraph) -> int:
    """Объединяет runs, если плейсхолдер разбит на части.

    Возвращает число исправлений (0 — не требовалось).
    """
    full = _paragraph_text(para)
    if "{{" not in full and "}}" not in full:
        return 0

    placeholders_in_full = PLACEHOLDER_RE.findall(full)
    if not placeholders_in_full:
        return 0

    placeholders_in_runs = PLACEHOLDER_RE.findall(
        "".join(r.text for r in para.runs if "{{" in r.text and "}}" in r.text)
    )
    if len(placeholders_in_runs) >= len(placeholders_in_full):
        return 0

    if not para.runs:
        return 0
    first = para.runs[0]
    first.text = full
    for run in para.runs[1:]:
        run.text = ""
    return 1


def normalize_runs_in_file(docx_path: Path) -> int:
    """Нормализует все параграфы файла. Возвращает число исправленных параграфов."""
    doc = DocxDocument(str(docx_path))
    fixed = 0
    for para in _iter_paragraphs(doc):
        fixed += _normalize_paragraph(para)
    if fixed > 0:
        doc.save(str(docx_path))
    return fixed


# ===== Автосопоставление известных полей =====
KNOWN_FIELDS: dict[str, dict] = {
    "case.case_number": {"description": "Номер дела", "source": "case"},
    "case.article": {"description": "Статья УК (полная)", "source": "case"},
    "case.article_code": {"description": "Номер статьи", "source": "case"},
    "case.article_part": {"description": "Часть статьи", "source": "case"},
    "case.initiated_at": {"description": "Дата возбуждения", "source": "case"},
    "case.current_deadline": {"description": "Текущий срок", "source": "case"},
    "case.originating_agency": {"description": "Орган возбуждения", "source": "case"},
    "profile.full_name": {"description": "ФИО следователя", "source": "profile"},
    "profile.position": {"description": "Должность", "source": "profile"},
    "profile.rank": {"description": "Звание", "source": "profile"},
    "profile.organization_name": {"description": "Место работы", "source": "profile"},
    "accused.full_name": {"description": "ФИО обвиняемого", "source": "party_accused"},
    "accused.birth_date": {"description": "Дата рождения обвиняемого", "source": "party_accused"},
    "accused.registration_address": {
        "description": "Адрес регистрации обвиняемого",
        "source": "party_accused",
    },
    "accused.passport_id": {"description": "Паспорт обвиняемого", "source": "party_accused"},
    "victim.full_name": {"description": "ФИО потерпевшего", "source": "party_victim"},
    "victim.birth_date": {"description": "Дата рождения потерпевшего", "source": "party_victim"},
    "current_date": {"description": "Текущая дата", "source": "service"},
}


def build_fields_schema(placeholders: list[str]) -> dict:
    """Формирует JSON-схему сопоставления."""
    fields = []
    for ph in placeholders:
        known = KNOWN_FIELDS.get(ph)
        fields.append(
            {
                "field": ph,
                "raw": "{{ " + ph + " }}",
                "auto_mapped": known is not None,
                "description": known.get("description", "") if known else "",
                "source": known.get("source", "manual") if known else "manual",
            }
        )
    auto_count = sum(1 for f in fields if f["auto_mapped"])
    return {
        "fields": fields,
        "auto_mapped_count": auto_count,
        "total": len(fields),
    }
