"""Токены по telegram_id."""

from __future__ import annotations


class SessionStore:
    def __init__(self) -> None:
        self._tokens: dict[int, str] = {}

    def get(self, telegram_id: int) -> str | None:
        return self._tokens.get(telegram_id)

    def set(self, telegram_id: int, token: str) -> None:
        self._tokens[telegram_id] = token

    def clear(self, telegram_id: int) -> None:
        self._tokens.pop(telegram_id, None)


sessions = SessionStore()
