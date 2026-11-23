"""Тесты этапа 5: парсер сущностей и Inbox."""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from case_workspace.auth.service import AuthService
from case_workspace.db.models import Base
from case_workspace.identifiers.service import IdentifierService
from case_workspace.inbox import models as _inbox  # noqa: F401
from case_workspace.inbox.entity_parser import extract_entities
from case_workspace.inbox.models import InboxSource, InboxStatus
from case_workspace.inbox.service import InboxService
from case_workspace.participants.models import PartyRole
from case_workspace.participants.service import PartyService
from case_workspace.projects.service import CaseService


SAMPLE = """
Дело № 26121040001
Обвиняемый: Петров Пётр Петрович
Карта: 9112 0020 1356 1354
Счёт: BY12 ALFA 3014 0000 0000 0000 0000
Телефон: +375 33 390-11-82
IP: 12.12.222.147
Дата: 15.01.2026
"""


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine, future=True)()
    yield s
    s.close()


@pytest.fixture
def setup(session):
    admin = AuthService(session).register_first_admin(
        login="admin", password="AaBb123!", full_name="X",
        organization_name="РОСК", organ_code="12", territorial_code="104",
    )
    case = CaseService(session).create_case(
        admin, article="205", initiated_at=date(2026, 1, 1), sequential_number="1"
    )
    PartyService(session).add_party(
        case.id, role=PartyRole.ACCUSED, full_name="Петров Пётр Петрович"
    )
    IdentifierService(session).add(case.id, "9112 0020 1356 1354", use_online=False)
    return {"session": session, "case": case}


def test_extract_entities_all() -> None:
    e = extract_entities(SAMPLE)
    assert "9112002013561354" in e["cards"]
    assert "BY12 ALFA 3014 0000 0000 0000 0000" in e["ibans"]
    assert "+375333901182" in e["phones"]
    assert "12.12.222.147" in e["ips"]
    assert "26121040001" in e["case_numbers"]
    assert "15.01.2026" in e["dates"]
    assert "Петров Пётр Петрович" in e["names"]


def test_extract_entities_empty() -> None:
    e = extract_entities("")
    assert e["cards"] == []
    assert e["case_numbers"] == []


def test_extract_entities_no_false_positive() -> None:
    e = extract_entities("Просто текст без идентификаторов")
    assert e["cards"] == []
    assert e["ibans"] == []
    assert e["phones"] == []
    assert e["ips"] == []
    assert e["case_numbers"] == []


def test_build_hypotheses(setup) -> None:
    svc = InboxService(setup["session"])
    analysis = svc.analyze_text(SAMPLE)
    hypotheses = analysis["hypotheses"]
    assert len(hypotheses) >= 1
    case_h = next((h for h in hypotheses if h["case_id"] == setup["case"].id), None)
    assert case_h is not None
    assert case_h["weight"] == "strong"
    assert any("номер дела" in r for r in case_h["reasons"])


def test_auto_tags(setup) -> None:
    svc = InboxService(setup["session"])
    analysis = svc.analyze_text(SAMPLE)
    tags = analysis["auto_tags"]
    assert "#карта" in tags
    assert "#счёт" in tags
    assert "#телефон" in tags
    assert "#ip" in tags
    assert "#номер_дела" in tags


def test_add_from_text(setup) -> None:
    svc = InboxService(setup["session"])
    item = svc.add_from_text(SAMPLE, source=InboxSource.PROGRAM)
    assert item.id is not None
    assert item.status == InboxStatus.NEW
    assert item.raw_text == SAMPLE.strip()


def test_attach_to_case(setup) -> None:
    svc = InboxService(setup["session"])
    item = svc.add_from_text(SAMPLE)
    svc.attach_to_case(item.id, setup["case"].id)
    item = svc.get(item.id)
    assert item.status == InboxStatus.ATTACHED
    assert item.attached_to_case_id == setup["case"].id


def test_ignore(setup) -> None:
    svc = InboxService(setup["session"])
    item = svc.add_from_text(SAMPLE)
    svc.ignore(item.id)
    item = svc.get(item.id)
    assert item.status == InboxStatus.IGNORED


def test_list_items(setup) -> None:
    svc = InboxService(setup["session"])
    svc.add_from_text(SAMPLE)
    svc.add_from_text("Другой текст")
    items = svc.list_items()
    assert len(items) == 2
    new_items = svc.list_items(InboxStatus.NEW)
    assert len(new_items) == 2


def test_delete(setup) -> None:
    svc = InboxService(setup["session"])
    item = svc.add_from_text(SAMPLE)
    svc.delete(item.id)
    assert svc.get(item.id) is None
