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

    def _log(self, login: str, result: str, attempt_number: int, lockout_level: int) -> None:
        self.session.add(
            AuthAttemptLog(
                login=login, source="program", result=result,
                attempt_number=attempt_number, lockout_level=lockout_level,
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
        user.failed_attempts = 0
        user.lockout_level = 0
        user.locked_until = None
        user.last_login_at = now
        self._log(login_norm, "success", 0, 0)
        self.session.commit()
        return user

    def create_user(
        self,
        admin: UserAccount,
        *,
        login: str,
        password: str,
        full_name: str,
        position: str = "",
        rank: str = "",
        organization_name: str = "",
        organ_code: str = "",
        territorial_code: str = "",
        role: Role = Role.USER,
    ) -> UserAccount:
        if admin.role != Role.ADMIN:
            raise errors.AuthError("Только администратор может создавать пользователей.")
        if not login.strip():
            raise errors.AuthError("Логин не может быть пустым.")
        if self.session.scalar(select(UserAccount).where(UserAccount.login == login.strip().lower())):
            raise errors.AuthError(f"Логин '{login}' уже занят.")
        policy_errors = security.validate_password_policy(password)
        if policy_errors:
            raise errors.PasswordPolicyError(" ".join(policy_errors))
        user = UserAccount(
            login=login.strip().lower(),
            password_hash=security.hash_password(password),
            role=role,
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

    def list_users(self) -> list[UserAccount]:
        return list(
            self.session.scalars(
                select(UserAccount)
                .where(UserAccount.is_deleted == False)  # noqa: E712
                .order_by(UserAccount.role, UserAccount.login)
            )
        )

    def register_user(
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
        if not self.has_users():
            raise errors.AuthError("Сначала должен быть зарегистрирован администратор.")
        if not login.strip():
            raise errors.AuthError("Логин не может быть пустым.")
        if self.session.scalar(
            select(UserAccount).where(UserAccount.login == login.strip().lower())
        ):
            raise errors.AuthError(f"Логин '{login}' уже занят.")
        policy_errors = security.validate_password_policy(password)
        if policy_errors:
            raise errors.PasswordPolicyError(" ".join(policy_errors))
        user = UserAccount(
            login=login.strip().lower(),
            password_hash=security.hash_password(password),
            role=Role.USER,
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

    def set_active(self, admin: UserAccount, user_id: int, active: bool) -> None:
        if admin.role != Role.ADMIN:
            raise errors.AuthError("Только администратор.")
        user = self.session.get(UserAccount, user_id)
        if user is None:
            raise errors.AuthError("Пользователь не найден.")
        if user.id == admin.id and not active:
            raise errors.AuthError("Нельзя деактивировать самого себя.")
        if user.role == Role.ADMIN and not active:
            other = self.session.scalar(
                select(UserAccount).where(
                    UserAccount.role == Role.ADMIN,
                    UserAccount.is_active == True,  # noqa: E712
                    UserAccount.id != user.id,
                )
            )
            if other is None:
                raise errors.AuthError("Нельзя деактивировать последнего администратора.")
        user.is_active = active
        self.session.commit()

    def change_password(self, user: UserAccount, current: str, new: str) -> None:
        if not security.verify_password(current, user.password_hash):
            raise errors.AuthError("Текущий пароль неверен.")
        policy_errors = security.validate_password_policy(new)
        if policy_errors:
            raise errors.PasswordPolicyError(" ".join(policy_errors))
        user.password_hash = security.hash_password(new)
        self.session.commit()
