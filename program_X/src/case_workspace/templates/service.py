"""Сервис работы с шаблонами."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from case_workspace.templates.models import Template, TemplateCategory
from case_workspace.templates.parser import (
    build_fields_schema,
    extract_placeholders,
    normalize_runs_in_file,
)

TEMPLATES_ROOT = Path("resources/templates")


def _category_from_path(path: Path) -> TemplateCategory:
    try:
        rel = path.relative_to(TEMPLATES_ROOT)
        first = rel.parts[0]
        return TemplateCategory(first)
    except (ValueError, KeyError):
        return TemplateCategory.OTHER


class TemplateService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def import_from_folder(
        self, path: Path, category: TemplateCategory | None = None
    ) -> Template:
        """Импортирует один DOCX-бланк: нормализует, парсит плейсхолдеры, сохраняет."""
        if not path.exists():
            raise ValueError(f"Файл не найден: {path}")
        if path.suffix.lower() != ".docx":
            raise ValueError("Поддерживаются только .docx-файлы.")

        # Копируем в resources/templates/<category>/, если ещё не там
        cat = category or _category_from_path(path)
        target_dir = TEMPLATES_ROOT / cat.value
        target_dir.mkdir(parents=True, exist_ok=True)
        if TEMPLATES_ROOT not in path.parents:
            target_path = target_dir / path.name
            shutil.copy2(path, target_path)
        else:
            target_path = path

        # Нормализуем runs
        normalize_runs_in_file(target_path)

        # Извлекаем плейсхолдеры
        placeholders = extract_placeholders(target_path)
        schema = build_fields_schema(placeholders)

        # Проверяем, есть ли уже такой
        existing = self.session.scalar(
            select(Template).where(Template.source_path == str(target_path))
        )
        if existing:
            existing.name = path.stem
            existing.category = cat
            existing.fields_schema = json.dumps(schema, ensure_ascii=False)
            existing.version += 1
            self.session.commit()
            return existing

        template = Template(
            name=path.stem,
            category=cat,
            source_path=str(target_path),
            fields_schema=json.dumps(schema, ensure_ascii=False),
        )
        self.session.add(template)
        self.session.commit()
        return template

    def scan_all(self) -> list[Template]:
        """Сканирует resources/templates/ и импортирует все DOCX."""
        if not TEMPLATES_ROOT.exists():
            return []
        imported: list[Template] = []
        for docx_path in TEMPLATES_ROOT.rglob("*.docx"):
            try:
                imported.append(self.import_from_folder(docx_path))
            except Exception as exc:  # noqa: BLE001
                print(f"WARN: {docx_path}: {exc}")
        return imported

    def list_templates(
        self, category: TemplateCategory | None = None
    ) -> list[Template]:
        q = select(Template).order_by(Template.category, Template.name)
        if category is not None:
            q = q.where(Template.category == category)
        return list(self.session.scalars(q))

    def get(self, template_id: int) -> Template | None:
        return self.session.get(Template, template_id)

    def delete(self, template_id: int) -> None:
        t = self.session.get(Template, template_id)
        if t:
            self.session.delete(t)
            self.session.commit()

    def toggle_favorite(self, template_id: int) -> Template:
        t = self.session.get(Template, template_id)
        if t is None:
            raise ValueError("Шаблон не найден.")
        t.is_favorite = not t.is_favorite
        self.session.commit()
        return t

    def get_fields_schema(self, template_id: int) -> dict:
        t = self.session.get(Template, template_id)
        if t is None:
            raise ValueError("Шаблон не найден.")
        if not t.fields_schema:
            return {"fields": [], "auto_mapped_count": 0, "total": 0}
        return json.loads(t.fields_schema)
