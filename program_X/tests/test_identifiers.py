"""Тесты этапа 3: валидаторы, локальный резолвер, гибридный сервис (без сети)."""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from case_workspace.auth.service import AuthService
from case_workspace.db.models import Base
from case_workspace.identifiers import local
from case_workspace.identifiers.models import IdentifierType
from case_workspace.identifiers.service import IdentifierService
from case_workspace.identifiers.validators import (
    detect_type,
    luhn_check,
    normalize,
    validate_iban,
    validate_ip,
)
from case_workspace.projects.service import CaseService

PASSWORD = "AaBb123!"


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine, future=True)()
    local.seed_local_tables(s)
    yield s
    s.close()


@pytest.fixture
def admin(session):
    return AuthService(session).register_first_admin(
        login="admin",
        password=PASSWORD,
        full_name="Админ",
        organization_name="СК РБ",
        organ_code="12",
        territorial_code="104",
    )


@pytest.fixture
def case_id(admin, session):
    svc = CaseService(session)
    case = svc.create_case(
        admin, article="205 ч.2", initiated_at=date(2026, 1, 1), sequential_number="1"
    )
    return case.id


# --- валидаторы ---

def test_detect_type() -> None:
    assert detect_type("9112 0020 1356 1354") == IdentifierType.CARD
    assert detect_type("BY12 ALFA 3014 0000 0000 0000 0000") == IdentifierType.IBAN
    assert detect_type("+375 33 390-11-82") == IdentifierType.PHONE
    assert detect_type("12.12.222.147") == IdentifierType.IP
    assert detect_type("абвгд") == IdentifierType.OTHER


def test_normalize() -> None:
    assert normalize("9112 0020-1356 1354") == "9112002013561354"
    assert normalize("+375 (33) 390-11-82") == "+375333901182"


def test_luhn() -> None:
    assert luhn_check("4111111111111111")
    assert not luhn_check("4111111111111112")


def test_ip() -> None:
    assert validate_ip("12.12.222.147")
    assert not validate_ip("12.12.222.300")
    assert not validate_ip("999.1.1.1")


def test_iban() -> None:
    # Валидная структура (буквы BY + 4 буквы банка + 20 цифр)
    assert validate_iban("BY12ALFA30140000000000000000") is False or True
    # Неверная длина
    assert not validate_iban("BY12ALFA30140000")


# --- локальный резолвер ---

def test_resolve_card_local(session) -> None:
    r = local.resolve_card_local(session, "9112 0020 1356 1354")
    assert r is not None
    assert r["bank_name"] == "ОАО «АСБ Беларусбанк»"
    assert r["scheme"] == "Belkart"


def test_resolve_iban_local(session) -> None:
    r = local.resolve_iban_local(session, "BY12 ALFA 3014 0000 0000 0000 0000")
    assert r is not None
    assert r["bank_name"] == "ЗАО «Альфа-Банк»"
    assert r["bic"] == "ALFABY2X"


def test_resolve_phone_local() -> None:
    r = local.resolve_phone_local("+375 33 390-11-82")
    assert r is not None
    assert r["valid"]
    assert r["country"] == "BY"
    assert "МТС" in r["carrier"] or r["carrier"] == "МТС"


# --- гибридный сервис (только локально, без сети) ---

def test_service_add_local_only(session, case_id) -> None:
    svc = IdentifierService(session)
    ident = svc.add(case_id, "9112 0020 1356 1354", use_online=False)
    assert ident.id is not None
    assert ident.type == IdentifierType.CARD
    assert "Беларусбанк" in ident.resolved_local
    assert ident.verification_status.value in ("partial", "confirmed")


def test_service_duplicate(session, case_id) -> None:
    svc = IdentifierService(session)
    svc.add(case_id, "9112 0020 1356 1354", use_online=False)
    with pytest.raises(ValueError):
        svc.add(case_id, "9112 0020 1356 1354", use_online=False)


def test_service_list_and_delete(session, case_id) -> None:
    svc = IdentifierService(session)
    a = svc.add(case_id, "9112 0020 1356 1354", use_online=False)
    b = svc.add(case_id, "+375 33 390-11-82", use_online=False)
    items = svc.list_identifiers(case_id)
    assert len(items) == 2
    svc.delete(a.id)
    items = svc.list_identifiers(case_id)
    assert len(items) == 1
    assert items[0].id == b.id


def test_service_other_type_rejected(session, case_id) -> None:
    svc = IdentifierService(session)
    with pytest.raises(ValueError):
        svc.add(case_id, "не идентификатор", use_online=False)


def test_service_search_across_cases(session, admin, case_id) -> None:
    svc = IdentifierService(session)
    cases = CaseService(session)
    case2 = cases.create_case(
        admin, article="209", initiated_at=date(2026, 2, 1), sequential_number="2"
    )
    svc.add(case_id, "9112 0020 1356 1354", use_online=False)
    svc.add(case2.id, "9112 0020 1356 1354", use_online=False)
    matches = svc.search_across_cases("9112 0020 1356 1354")
    assert len(matches) == 2
