"""Тесты этапа 2: дела, участники, сроки, эпизоды."""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from case_workspace.auth.service import AuthService
from case_workspace.db.models import Base, Role, UserAccount
from case_workspace.participants.models import PartyRole
from case_workspace.participants.service import PartyService
from case_workspace.projects.models import Case
from case_workspace.projects.service import CaseService
from case_workspace.projects.validators import (
    add_months,
    build_case_number,
    parse_article,
    validate_parts,
)

PASSWORD = "AaBb123!"


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine, future=True)()
    yield s
    s.close()


@pytest.fixture
def admin(session):
    auth = AuthService(session)
    return auth.register_first_admin(
        login="admin",
        password=PASSWORD,
        full_name="Админ",
        organization_name="СК РБ",
        organ_code="12",
        territorial_code="104",
    )


# --- validators ---


def test_add_months_normal() -> None:
    assert add_months(date(2026, 1, 1), 2) == date(2026, 3, 1)


def test_add_months_leap_year() -> None:
    assert add_months(date(2024, 1, 1), 2) == date(2024, 3, 1)


def test_add_months_end_of_month() -> None:
    assert add_months(date(2026, 1, 31), 2) == date(2026, 3, 31)


def test_parse_article() -> None:
    assert parse_article("205 ч.2") == ("205", "2")
    assert parse_article("ст. 205") == ("205", "")
    assert parse_article("212") == ("212", "")


def test_build_and_validate() -> None:
    number = build_case_number("26", "12", "104", "1")
    assert number == "26121040001"
    assert len(number) == 11
    assert validate_parts("26", "12", "104", "1") == []
    assert validate_parts("2", "12", "104", "1") != []
    assert validate_parts("26", "123", "104", "1") != []
    assert validate_parts("26", "12", "10", "1") != []


# --- cases ---


def test_create_case(admin, session) -> None:
    svc = CaseService(session)
    case = svc.create_case(
        admin,
        article="205 ч.2",
        initiated_at=date(2026, 1, 1),
        sequential_number="1",
    )
    assert case.case_number == "26121040001"
    assert case.article_code == "205"
    assert case.article_part == "2"
    assert case.current_deadline == date(2026, 3, 1)
    assert case.owner_id == admin.id
    assert case.is_episode is False


def test_create_case_duplicate(admin, session) -> None:
    svc = CaseService(session)
    svc.create_case(admin, article="205", initiated_at=date(2026, 1, 1), sequential_number="1")
    with pytest.raises(ValueError):
        svc.create_case(admin, article="209", initiated_at=date(2026, 1, 2), sequential_number="1")


def test_create_case_missing_organ(session) -> None:
    auth = AuthService(session)
    user = auth.register_first_admin(
        login="admin2", password=PASSWORD, full_name="X", organ_code="", territorial_code=""
    )
    svc = CaseService(session)
    with pytest.raises(ValueError):
        svc.create_case(user, article="205", initiated_at=date(2026, 1, 1), sequential_number="1")


def test_list_cases_admin_sees_all(admin, session) -> None:
    auth = AuthService(session)
    helper = auth.create_user(
        admin, login="helper", password=PASSWORD, full_name="Помощник",
        organ_code="12", territorial_code="104",
    )
    svc = CaseService(session)
    svc.create_case(admin, article="205", initiated_at=date(2026, 1, 1), sequential_number="1")
    svc.create_case(helper, article="209", initiated_at=date(2026, 1, 2), sequential_number="2")

    assert len(svc.list_cases(admin)) == 2
    assert len(svc.list_cases(helper)) == 1  # только своё


def test_extend_deadline(admin, session) -> None:
    svc = CaseService(session)
    case = svc.create_case(
        admin, article="205", initiated_at=date(2026, 1, 1), sequential_number="1"
    )
    svc.extend_deadline(case.id, date(2026, 5, 1), reason="Продление по делу")
    refreshed = svc.get_case(case.id)
    assert refreshed is not None
    assert refreshed.current_deadline == date(2026, 5, 1)


def test_episode_without_number(admin, session) -> None:
    svc = CaseService(session)
    parent = svc.create_case(
        admin, article="205", initiated_at=date(2026, 1, 1), sequential_number="1"
    )
    episode = svc.create_episode(
        admin, parent.id, article="205 ч.2", initiated_at=date(2026, 1, 15)
    )
    assert episode.case_number is None
    assert episode.is_episode is True
    assert episode.parent_case_id == parent.id


# --- parties ---


def test_add_party(admin, session) -> None:
    cases = CaseService(session)
    parties = PartyService(session)
    case = cases.create_case(
        admin, article="205", initiated_at=date(2026, 1, 1), sequential_number="1"
    )
    party = parties.add_party(
        case.id,
        role=PartyRole.ACCUSED,
        full_name="Иванов Иван Иванович",
        birth_date=date(1980, 1, 1),
        passport_id="MP1234567",
        contact_phone="+375291234567",
    )
    assert party.id is not None
    assert len(parties.list_parties(case.id)) == 1
    parties.delete_party(party.id)
    assert parties.list_parties(case.id) == []


def test_add_party_empty_name(session) -> None:
    parties = PartyService(session)
    with pytest.raises(ValueError):
        parties.add_party(1, role=PartyRole.VICTIM, full_name="   ")


# --- users ---


def test_user_cannot_create_user(session) -> None:
    auth = AuthService(session)
    admin = auth.register_first_admin(
        login="admin", password=PASSWORD, full_name="A", organ_code="12", territorial_code="104"
    )
    helper = auth.create_user(admin, login="h", password=PASSWORD, full_name="H", role=Role.USER)
    from case_workspace.domain import errors
    with pytest.raises(errors.AuthError):
        auth.create_user(helper, login="x", password=PASSWORD, full_name="X")


def test_cannot_deactivate_last_admin(session) -> None:
    auth = AuthService(session)
    admin = auth.register_first_admin(
        login="admin", password=PASSWORD, full_name="A", organ_code="12", territorial_code="104"
    )
    from case_workspace.domain import errors
    with pytest.raises(errors.AuthError):
        auth.set_active(admin, admin.id, False)