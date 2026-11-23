"""Тесты этапа 4.1: парсинг DOCX и нормализация runs."""

from pathlib import Path

import pytest
from docx import Document
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from case_workspace.db.models import Base
from case_workspace.templates import models as _templates  # noqa: F401
from case_workspace.templates.models import TemplateCategory
from case_workspace.templates.parser import (
    build_fields_schema,
    extract_placeholders,
    normalize_runs_in_file,
)
from case_workspace.templates.service import TemplateService


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine, future=True)()
    yield s
    s.close()


def _create_test_docx(path: Path, broken: bool = False) -> None:
    doc = Document()
    doc.add_paragraph("Дело № {{ case.case_number }}")
    doc.add_paragraph("Статья: {{ case.article_code }} ч.{{ case.article_part }}")
    if broken:
        p = doc.add_paragraph()
        p.add_run("Следователь: ")
        p.add_run("{{ profile.")
        p.add_run("full_name }}")
    else:
        doc.add_paragraph("Следователь: {{ profile.full_name }}")
    doc.save(str(path))


def test_extract_placeholders(tmp_path) -> None:
    p = tmp_path / "t.docx"
    _create_test_docx(p)
    ph = extract_placeholders(p)
    assert "case.case_number" in ph
    assert "case.article_code" in ph
    assert "profile.full_name" in ph


def test_broken_placeholder_still_extracted(tmp_path) -> None:
    """extract_placeholders соединяет runs перед поиском, поэтому разбитый
    плейсхолдер тоже извлекается. Это правильное поведение — нормализация
    нужна только для docxtpl (рендеринг)."""
    p = tmp_path / "t.docx"
    _create_test_docx(p, broken=True)
    ph = extract_placeholders(p)
    assert "case.case_number" in ph
    assert "profile.full_name" in ph  # извлекается, несмотря на разбивку


def test_normalize_merges_runs(tmp_path) -> None:
    """После нормализации первый run содержит весь текст плейсхолдера,
    а остальные — пусты. Это нужно для docxtpl."""
    from docx import Document

    p = tmp_path / "t.docx"
    _create_test_docx(p, broken=True)
    fixed = normalize_runs_in_file(p)
    assert fixed >= 1
    doc = Document(str(p))
    # Параграф №3 (индекс 2) — тот, что был разбит
    para = doc.paragraphs[2]
    full_text = "".join(r.text for r in para.runs)
    assert "{{ profile.full_name }}" in full_text
    # Первый run содержит весь текст
    assert "{{ profile.full_name }}" in para.runs[0].text


def test_normalize_runs(tmp_path) -> None:
    p = tmp_path / "t.docx"
    _create_test_docx(p, broken=True)
    fixed = normalize_runs_in_file(p)
    assert fixed >= 1
    ph = extract_placeholders(p)
    assert "profile.full_name" in ph


def test_build_fields_schema() -> None:
    schema = build_fields_schema(["case.case_number", "custom.field"])
    assert schema["total"] == 2
    assert schema["auto_mapped_count"] == 1
    by_field = {f["field"]: f for f in schema["fields"]}
    assert by_field["case.case_number"]["auto_mapped"] is True
    assert by_field["custom.field"]["auto_mapped"] is False


def test_import_template(tmp_path, session) -> None:
    p = tmp_path / "postanovlenie.docx"
    _create_test_docx(p)
    svc = TemplateService(session)
    template = svc.import_from_folder(p, category=TemplateCategory.OPERATIONS)
    assert template.id is not None
    assert template.category == TemplateCategory.OPERATIONS
    assert template.name == "postanovlenie"
    schema = svc.get_fields_schema(template.id)
    assert schema["total"] >= 3


def test_list_templates(session, tmp_path) -> None:
    svc = TemplateService(session)
    p1 = tmp_path / "t1.docx"
    p2 = tmp_path / "t2.docx"
    _create_test_docx(p1)
    _create_test_docx(p2)
    svc.import_from_folder(p1, category=TemplateCategory.BANKS)
    svc.import_from_folder(p2, category=TemplateCategory.PROTOCOLS)
    banks = svc.list_templates(TemplateCategory.BANKS)
    assert len(banks) == 1
    all_t = svc.list_templates()
    assert len(all_t) == 2


def test_favorite_toggle(session, tmp_path) -> None:
    p = tmp_path / "t.docx"
    _create_test_docx(p)
    svc = TemplateService(session)
    t = svc.import_from_folder(p, category=TemplateCategory.BANKS)
    assert not t.is_favorite
    t = svc.toggle_favorite(t.id)
    assert t.is_favorite
    t = svc.toggle_favorite(t.id)
    assert not t.is_favorite
