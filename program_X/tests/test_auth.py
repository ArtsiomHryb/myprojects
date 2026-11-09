"""Тесты этапа 1: регистрация, вход, политика, блокировка."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from case_workspace.auth import security
from case_workspace.auth.service import AuthService
from case_workspace.db.models import Base, UserAccount
from case_workspace.domain import errors

VALID_PASSWORD = "AaBb123!"


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)
    s = Session()
    yield s
    s.close()


def test_register_and_login(session) -> None:
    auth = AuthService(session)
    user = auth.register_first_admin(
        login="admin", password=VALID_PASSWORD, full_name="Тест Админ"
    )
    assert user.role.value == "admin"
    assert auth.has_users() is True

    authed = auth.authenticate("admin", VALID_PASSWORD)
    assert authed.id == user.id


def test_second_admin_not_allowed(session) -> None:
    auth = AuthService(session)
    auth.register_first_admin(login="admin", password=VALID_PASSWORD, full_name="А")
    with pytest.raises(errors.AuthError):
        auth.register_first_admin(login="admin2", password=VALID_PASSWORD, full_name="Б")


def test_password_policy() -> None:
    assert security.validate_password_policy(VALID_PASSWORD) == []
    assert security.validate_password_policy("short") != []
    assert security.validate_password_policy("AAAAAAAA!1") != []
    assert security.validate_password_policy("aaaaaaaa!1") != []
    assert security.validate_password_policy("Aaaa!!!!x") != []
    assert security.validate_password_policy("Aaaa1111") != []


def test_wrong_password_decrements_attempts(session) -> None:
    auth = AuthService(session)
    auth.register_first_admin(login="admin", password=VALID_PASSWORD, full_name="А")
    with pytest.raises(errors.InvalidCredentialsError) as exc:
        auth.authenticate("admin", "wrong")
    assert exc.value.attempts_left == 4


def test_lockout_after_five_failures(session) -> None:
    auth = AuthService(session)
    auth.register_first_admin(login="admin", password=VALID_PASSWORD, full_name="А")
    for _ in range(4):
        with pytest.raises(errors.InvalidCredentialsError):
            auth.authenticate("admin", "wrong")

    # 5-я попытка → блокировка
    with pytest.raises(errors.AccountLockedError):
        auth.authenticate("admin", "wrong")

    # И корректный пароль не пускает, пока блокировка активна
    with pytest.raises(errors.AccountLockedError):
        auth.authenticate("admin", VALID_PASSWORD)


def test_lockout_expires_and_resets(session) -> None:
    auth = AuthService(session)
    user = auth.register_first_admin(login="admin", password=VALID_PASSWORD, full_name="А")
    for _ in range(5):
        try:
            auth.authenticate("admin", "wrong")
        except (errors.InvalidCredentialsError, errors.AccountLockedError):
            pass

    # Принудительно истекаем блокировку
    stored = session.get(UserAccount, user.id)
    stored.locked_until = datetime.utcnow() - timedelta(minutes=1)
    session.commit()

    authed = auth.authenticate("admin", VALID_PASSWORD)
    assert authed.id == user.id
    # После успеха — блокировка сброшена
    assert authed.lockout_level == 0
    assert authed.failed_attempts == 0