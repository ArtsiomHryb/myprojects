"""Зависимости FastAPI: БД и текущий пользователь."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from case_workspace.auth_api.jwt_service import ApiAuthService
from case_workspace.db.base import init_db, session_factory

_engine = init_db()
_Session = session_factory(_engine)


def get_db():
    session = _Session()
    try:
        yield session
    finally:
        session.close()


def get_current_payload(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="no token")
    token = authorization.split(" ", 1)[1].strip()
    auth = ApiAuthService(db)
    payload = auth.verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="invalid or expired token")
    return payload
