"""Сервис аутентификации."""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from case_workspace.auth import security
from case_workspace.db.models import AuthAttemptLog, Role, UserAccount
from case_workspace.domain import errors


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session

    # --- регистрация ---

    def has_users(self) -> bool:
        return self.session.scalar(select(UserAccount.id).limit(1)) is not None

    def register_first_admin(
        self,
        *,
        login: str,
        password: str,
        full_name: str,
        position: str = "",
        rank: str = "",
        organization_name: str = "",
        organ_code: str = "",
        territorial_code: str = "",
    ) -> UserAccount:
        if self.has_users():
            raise errors.AuthError("Первый администратор уже зарегистрирован.")

        policy_errors = security.validate_password_policy(password)
        if policy_errors:
            raise errors.PasswordPolicyError(" ".join(policy_errors))

        if organ_code and not (organ_code.isdigit() and len(organ_code) == 2):
            raise errors.AuthError("Код органа должен содержать 2 цифры.")
        if territorial_code and not (territorial_code.isdigit() and len(territorial_code) == 3):
            raise errors.AuthError("Территориальный код должен содержать 3 цифры.")
        if not login.strip():
            raise errors.AuthError("Логин не может быть пустым.")

        user = UserAccount(
            login=login.strip().lower(),
            password_hash=security.hash_password(password),
            role=Role.ADMIN,
            full_name=full_name.strip(),
            position=position.strip(),
            rank=rank.strip(),
            organization_name=organization_name.strip(),
            organ_code=organ_code.strip(),
            territorial_code=territorial_code.strip(),
        )
        self.session.add(user)
        self.session.commit()
        return user

    # --- вход ---

    def _log(self, login: str, result: str, attempt_number: int, lockout_level: int) -> None:
        self.session.add(
            AuthAttemptLog(
                login=login,
                source="program",
                result=result,
                attempt_number=attempt_number,
                lockout_level=lockout_level,
            )
        )

    def authenticate(self, login: str, password: str) -> UserAccount:
        login_norm = login.strip().lower()
        now = datetime.utcnow()

        user = self.session.scalar(select(UserAccount).where(UserAccount.login == login_norm))

        if user is None:
            self._log(login_norm, "invalid", 0, 0)
            self.session.commit()
            raise errors.InvalidCredentialsError(attempts_left=security.MAX_FAILED_BEFORE_LOCK)

        if not user.is_active or user.is_deleted:
            self._log(login_norm, "inactive", 0, user.lockout_level)
            self.session.commit()
            raise errors.AuthError("Учётная запись деактивирована.")

        if user.locked_until and user.locked_until > now:
            self._log(login_norm, "locked", user.failed_attempts, user.lockout_level)
            self.session.commit()
            raise errors.AccountLockedError(user.locked_until)

        # Истёк срок блокировки — сбрасываем счётчик попыток (уровень сохраняем)
        if user.locked_until and user.locked_until <= now:
            user.failed_attempts = 0
            user.locked_until = None

        if not security.verify_password(password, user.password_hash):
            user.failed_attempts += 1
            attempts_left = max(0, security.MAX_FAILED_BEFORE_LOCK - user.failed_attempts)

            if user.failed_attempts >= security.MAX_FAILED_BEFORE_LOCK:
                user.lockout_level += 1
                minutes = security.calculate_lockout_minutes(user.lockout_level)
                user.locked_until = now + timedelta(minutes=minutes)
                user.failed_attempts = 0
                self._log(login_norm, "locked", 0, user.lockout_level)
                self.session.commit()
                raise errors.AccountLockedError(user.locked_until)

            self._log(login_norm, "invalid", user.failed_attempts, user.lockout_level)
            self.session.commit()
            raise errors.InvalidCredentialsError(attempts_left=attempts_left)

        # Успех
        user.failed_attempts = 0
        user.lockout_level = 0
        user.locked_until = None
        user.last_login_at = now
        self._log(login_norm, "success", 0, 0)
        self.session.commit()
        return user