"""Тесты этапа 4.2: рендеринг документов."""

from datetime import date
from pathlib import Path

import pytest
from docx import Document as DocxDocument
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from case_workspace.auth.service import AuthService
from case_workspace.db.models import Base
from case_workspace.documents import models as _docs  # noqa: F401
from case_workspace.documents.models import DocumentStatus, DocumentType
from case_workspace.documents.services import DocumentService
from case_workspace.participants.models import PartyRole
from case_workspace.participants.service import PartyService
from case_workspace.projects.service import CaseService
from case_workspace.templates.models import TemplateCategory
from case_workspace.templates.service import TemplateService


PASSWORD = "AaBb123!"


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine, future=True)()
    yield s
    s.close()


@pytest.fixture
def setup(tmp_path, session):
    # Бланк
    tpl_path = tmp_path / "postanovlenie.docx"
    doc = DocxDocument()
    doc.add_paragraph("Дело № {{ case.case_number }}")
    doc.add_paragraph("Следователь: {{ profile.full_name }}")
    doc.add_paragraph("Обвиняемый: {{ accused.full_name }}")
    doc.add_paragraph("Статья: {{ case.article_code }} ч.{{ case.article_part }}")
    doc.save(str(tpl_path))

    admin = AuthService(session).register_first_admin(
        login="admin",
        password=PASSWORD,
        full_name="Сидоров Сидор",
        organization_name="РОСК",
        organ_code="12",
        territorial_code="104",
    )
    case = CaseService(session).create_case(
        admin, article="205 ч.2", initiated_at=date(2026, 1, 1), sequential_number="1"
    )
    PartyService(session).add_party(
        case.id, role=PartyRole.ACCUSED, full_name="Иванов Иван"
    )
    template = TemplateService(session).import_from_folder(
        tpl_path, category=TemplateCategory.OPERATIONS
    )
    return {"session": session, "admin": admin, "case": case, "template": template}


def test_build_context(setup) -> None:
    svc = DocumentService(setup["session"])
    ctx = svc.build_context(setup["case"].id)
    assert ctx["case"]["case_number"] == "26121040001"
    assert ctx["case"]["article_code"] == "205"
    assert ctx["case"]["article_part"] == "2"
    assert ctx["profile"]["full_name"] == "Сидоров Сидор"
    assert ctx["accused"]["full_name"] == "Иванов Иван"


def test_build_context_with_overrides(setup) -> None:
    svc = DocumentService(setup["session"])
    ctx = svc.build_context(
        setup["case"].id,
        extra_data={"custom.osnovanie": "Заявление потерпевшего"},
    )
    assert ctx["custom"]["osnovanie"] == "Заявление потерпевшего"


def test_render_creates_document(setup) -> None:
    svc = DocumentService(setup["session"])
    doc = svc.render(setup["template"].id, setup["case"].id, convert_to_pdf=False)
    assert doc.id is not None
    assert doc.doc_type == DocumentType.GENERATED
    assert doc.status == DocumentStatus.DRAFT
    assert doc.version == 1
    assert doc.rendered_at is not None


def test_render_creates_version(setup) -> None:
    svc = DocumentService(setup["session"])
    doc = svc.render(setup["template"].id, setup["case"].id, convert_to_pdf=False)
    versions = svc.list_versions(doc.id)
    assert len(versions) == 1
    assert versions[0].version == 1
    assert Path(versions[0].file_path).exists()


def test_render_substitutes_data(setup) -> None:
    svc = DocumentService(setup["session"])
    doc = svc.render(setup["template"].id, setup["case"].id, convert_to_pdf=False)
    version = svc.list_versions(doc.id)[0]
    rendered = DocxDocument(version.file_path)
    text = "\n".join(p.text for p in rendered.paragraphs)
    assert "26121040001" in text
    assert "Сидоров Сидор" in text
    assert "Иванов Иван" in text
    assert "{{" not in text


def test_list_documents(setup) -> None:
    svc = DocumentService(setup["session"])
    svc.render(setup["template"].id, setup["case"].id, convert_to_pdf=False)
    svc.render(setup["template"].id, setup["case"].id, convert_to_pdf=False)
    docs = svc.list_documents(setup["case"].id)
    assert len(docs) == 2


def test_delete_document(setup) -> None:
    svc = DocumentService(setup["session"])
    doc = svc.render(setup["template"].id, setup["case"].id, convert_to_pdf=False)
    version_path = Path(svc.list_versions(doc.id)[0].file_path)
    assert version_path.exists()
    svc.delete(doc.id)
    assert svc.get(doc.id) is None
    assert not version_path.exists()
