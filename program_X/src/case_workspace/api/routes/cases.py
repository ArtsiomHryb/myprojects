"""Эндпоинты дел."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from case_workspace.api.deps import get_current_payload, get_db
from case_workspace.api.schemas import CaseDetail, CaseItem
from case_workspace.db.models import UserAccount
from case_workspace.projects.models import Case
from case_workspace.projects.service import CaseService

router = APIRouter(prefix="/cases", tags=["cases"])


def _get_user(db: Session, payload: dict) -> UserAccount:
    user = db.get(UserAccount, int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="user not found")
    return user


def _case_to_item(c: Case, days_left: int | None) -> CaseItem:
    return CaseItem(
        id=c.id,
        case_number=c.case_number,
        article=c.article,
        initiated_at=c.initiated_at.strftime("%d.%m.%Y") if c.initiated_at else "",
        current_deadline=(
            c.current_deadline.strftime("%d.%m.%Y") if c.current_deadline else ""
        ),
        days_left=days_left,
        status=c.location_status.value,
    )


@router.get("", response_model=list[CaseItem])
def list_cases(
    payload: dict = Depends(get_current_payload),
    db: Session = Depends(get_db),
) -> list[CaseItem]:
    user = _get_user(db, payload)
    svc = CaseService(db)
    cases = svc.list_cases(user)
    return [_case_to_item(c, svc.days_left(c)) for c in cases]


@router.get("/{case_number}", response_model=CaseDetail)
def get_case(
    case_number: str,
    payload: dict = Depends(get_current_payload),
    db: Session = Depends(get_db),
) -> CaseDetail:
    user = _get_user(db, payload)
    case = db.scalar(select(Case).where(Case.case_number == case_number))
    if case is None:
        raise HTTPException(status_code=404, detail="case not found")
    svc = CaseService(db)
    days = svc.days_left(case)
    parties_data = [
        {
            "role": p.role.value,
            "full_name": p.full_name,
            "birth_date": p.birth_date.strftime("%d.%m.%Y") if p.birth_date else "",
            "passport_id": p.passport_id,
            "contact_phone": p.contact_phone,
        }
        for p in case.parties
    ]
    return CaseDetail(
        id=case.id,
        case_number=case.case_number,
        article=case.article,
        initiated_at=case.initiated_at.strftime("%d.%m.%Y") if case.initiated_at else "",
        current_deadline=(
            case.current_deadline.strftime("%d.%m.%Y") if case.current_deadline else ""
        ),
        days_left=days,
        status=case.location_status.value,
        originating_agency=case.originating_agency,
        accused_name=case.accused_name,
        victim_name=case.victim_name,
        parties=parties_data,
    )
