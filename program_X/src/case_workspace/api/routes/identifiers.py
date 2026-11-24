"""Эндпоинты идентификаторов."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from case_workspace.api.deps import get_current_payload, get_db
from case_workspace.api.schemas import ResolveRequest
from case_workspace.identifiers.service import IdentifierService

router = APIRouter(prefix="/identifiers", tags=["identifiers"])


@router.post("/resolve")
def resolve(
    req: ResolveRequest,
    _payload: dict = Depends(get_current_payload),
    db: Session = Depends(get_db),
) -> dict:
    svc = IdentifierService(db)
    result = svc.resolve(req.value, use_online=True)
    return result


@router.post("/search")
def search(
    req: ResolveRequest,
    _payload: dict = Depends(get_current_payload),
    db: Session = Depends(get_db),
) -> dict:
    svc = IdentifierService(db)
    matches = svc.search_across_cases(req.value)
    return {
        "matches": [
            {
                "case_id": m.case_id,
                "identifier_id": m.id,
                "type": m.type.value,
                "value": m.value,
            }
            for m in matches
        ]
    }
