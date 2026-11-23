"""Сервис чёрного списка Telegram-аккаунтов."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from case_workspace.auth_api.models import TelegramBlacklist


class BlacklistService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def is_blocked(self, telegram_id: int) -> bool:
        return (
            self.session.scalar(
                select(TelegramBlacklist).where(
                    TelegramBlacklist.telegram_id == telegram_id
                )
            )
            is not None
        )

    def add(
        self,
        telegram_id: int,
        username: str = "",
        reason: str = "",
        blocked_by: str = "auto",
    ) -> TelegramBlacklist:
        existing = self.session.get(TelegramBlacklist, telegram_id)
        if existing is not None:
            existing.reason = reason
            existing.blocked_by = blocked_by
            self.session.commit()
            return existing
        b = TelegramBlacklist(
            telegram_id=telegram_id,
            username=username,
            reason=reason,
            blocked_by=blocked_by,
        )
        self.session.add(b)
        self.session.commit()
        return b

    def remove(self, telegram_id: int) -> None:
        b = self.session.get(TelegramBlacklist, telegram_id)
        if b:
            self.session.delete(b)
            self.session.commit()

    def list_all(self) -> list[TelegramBlacklist]:
        return list(self.session.scalars(select(TelegramBlacklist)))
