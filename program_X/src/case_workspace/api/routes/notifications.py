"""Эндпоинты уведомлений."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from case_workspace.api.deps import get_current_payload, get_db
from case_workspace.api.schemas import NotificationItem
from case_workspace.auth_api.notifications import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _to_item(n) -> NotificationItem:
    try:
        md = json.loads(n.metadata_json) if n.metadata_json else {}
    except ValueError:
        md = {}
    return NotificationItem(
        id=n.id,
        type=n.type.value,
        severity=n.severity.value,
        title=n.title,
        body=n.body,
        created_at=n.created_at.isoformat(),
        read_at=n.read_at.isoformat() if n.read_at else None,
        metadata=md,
    )


@router.get("", response_model=list[NotificationItem])
def list_notifications(
    unread_only: bool = False,
    _payload: dict = Depends(get_current_payload),
    db: Session = Depends(get_db),
) -> list[NotificationItem]:
    svc = NotificationService(db)
    items = svc.list_unread() if unread_only else svc.list_all()
    return [_to_item(n) for n in items]


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: int,
    _payload: dict = Depends(get_current_payload),
    db: Session = Depends(get_db),
) -> dict:
    svc = NotificationService(db)
    return {"ok": svc.mark_read(notification_id)}
