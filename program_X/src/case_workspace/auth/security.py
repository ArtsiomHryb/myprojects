"""Хеширование паролей, политика пароля, блокировки."""

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

_hasher = PasswordHasher()

# Прогрессия блокировок: 1 → 5 → 15 → 45 → 120 (потолок)
LOCKOUT_MINUTES = [1, 5, 15, 45, 120]
MAX_FAILED_BEFORE_LOCK = 5


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError):
        return False


def validate_password_policy(password: str) -> list[str]:
    """8–10 символов, ≥2 заглавные, ≥2 строчные, ≥1 цифра, ≥1 символ."""
    errors: list[str] = []
    if not (8 <= len(password) <= 10):
        errors.append("Пароль должен быть от 8 до 10 символов.")
    if sum(1 for c in password if c.isupper()) < 2:
        errors.append("Нужно минимум 2 заглавные буквы.")
    if sum(1 for c in password if c.islower()) < 2:
        errors.append("Нужно минимум 2 строчные буквы.")
    if sum(1 for c in password if c.isdigit()) < 1:
        errors.append("Нужно минимум 1 цифра.")
    if sum(1 for c in password if not c.isalnum()) < 1:
        errors.append("Нужно минимум 1 специальный символ.")
    return errors


def calculate_lockout_minutes(lockout_level: int) -> int:
    if lockout_level <= 0:
        return 0
    idx = min(lockout_level - 1, len(LOCKOUT_MINUTES) - 1)
    return LOCKOUT_MINUTES[idx]