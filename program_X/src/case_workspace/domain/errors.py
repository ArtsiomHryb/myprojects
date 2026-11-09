"""Доменные ошибки."""

from datetime import datetime


class AuthError(Exception):
    """Общая ошибка аутентификации."""


class InvalidCredentialsError(AuthError):
    def __init__(self, attempts_left: int) -> None:
        self.attempts_left = attempts_left
        super().__init__(f"Неверный логин или пароль. Осталось попыток: {attempts_left}")


class AccountLockedError(AuthError):
    def __init__(self, locked_until: datetime) -> None:
        self.locked_until = locked_until
        super().__init__(f"Учётная запись заблокирована до {locked_until:%Y-%m-%d %H:%M:%S}")


class PasswordPolicyError(AuthError):
    """Нарушение политики пароля."""