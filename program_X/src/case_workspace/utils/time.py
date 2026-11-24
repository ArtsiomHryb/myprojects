"""Хелперы времени: naive UTC для совместимости с DateTime."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Naive UTC — совместим с SQLAlchemy DateTime (без tzinfo).

    Использовать везде вместо datetime.utcnow() (deprecated)
    и вместо datetime.now(UTC) (aware — несовместим с колонками).
    """
    return datetime.now(UTC).replace(tzinfo=None)
