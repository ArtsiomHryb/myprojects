"""Сервис уведомлений."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from case_workspace.auth_api.models import (
    Notification,
    NotificationType,
    Severity,
)


class NotificationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        type: NotificationType,
        title: str,
        body: str = "",
        severity: Severity = Severity.INFO,
        source: str = "program",
        metadata: dict | None = None,
    ) -> Notification:
        n = Notification(
            type=type,
            severity=severity,
            title=title,
            body=body,
            source=source,
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
        )
        self.session.add(n)
        self.session.commit()
        return n

    def list_unread(self, limit: int = 100) -> list[Notification]:
        return list(
            self.session.scalars(
                select(Notification)
                .where(Notification.read_at == None)  # noqa: E712
                .order_by(Notification.created_at.desc())
                .limit(limit)
            )
        )

    def list_all(self, limit: int = 200) -> list[Notification]:
        return list(
            self.session.scalars(
                select(Notification).order_by(Notification.created_at.desc()).limit(limit)
            )
        )

    def mark_read(self, notification_id: int) -> bool:
        n = self.session.get(Notification, notification_id)
        if n is None:
            return False
        n.read_at = datetime.now(UTC)
        self.session.commit()
        return True

    def mark_all_read(self) -> int:
        rows = list(
            self.session.scalars(
                select(Notification).where(Notification.read_at == None)  # noqa: E712
            )
        )
        now = datetime.now(UTC)
        for n in rows:
            n.read_at = now
        self.session.commit()
        return len(rows)
