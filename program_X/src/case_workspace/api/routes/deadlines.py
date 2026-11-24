"""Эндпоинты сроков."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from case_workspace.api.deps import get_current_payload, get_db
from case_workspace.api.schemas import DeadlineItem
from case_workspace.db.models import UserAccount
from case_workspace.projects.service import CaseService

router = APIRouter(prefix="/deadlines", tags=["deadlines"])


@router.get("", response_model=list[DeadlineItem])
def list_deadlines(
    days: int = 30,
    payload: dict = Depends(get_current_payload),
    db: Session = Depends(get_db),
) -> list[DeadlineItem]:
    user = db.get(UserAccount, int(payload["sub"]))
    if user is None:
        return []
    svc = CaseService(db)
    cases = svc.list_cases(user)
    today = date.today()
    limit = today + timedelta(days=days)
    result: list[DeadlineItem] = []
    for c in cases:
        if c.current_deadline is None:
            continue
        if c.current_deadline > limit:
            continue
        result.append(
            DeadlineItem(
                case_id=c.id,
                case_number=c.case_number,
                article=c.article,
                current_deadline=c.current_deadline.strftime("%d.%m.%Y"),
                days_left=(c.current_deadline - today).days,
            )
        )
    result.sort(key=lambda x: x.days_left)
    return result
