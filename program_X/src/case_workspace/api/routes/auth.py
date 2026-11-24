"""Эндпоинты аутентификации."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from case_workspace.api.deps import get_current_payload, get_db
from case_workspace.api.schemas import StatusResponse, VerifyRequest, VerifyResponse
from case_workspace.auth_api.blacklist import BlacklistService
from case_workspace.auth_api.jwt_service import ApiAuthService
from case_workspace.auth_api.models import NotificationType, Severity
from case_workspace.auth_api.notifications import NotificationService
from case_workspace.domain import errors

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/verify", response_model=VerifyResponse)
def verify(req: VerifyRequest, db: Session = Depends(get_db)) -> VerifyResponse:
    bl = BlacklistService(db)
    if bl.is_blocked(req.telegram_id):
        raise HTTPException(status_code=403, detail="blacklisted")

    api_auth = ApiAuthService(db)
    try:
        result = api_auth.login_with_password(
            telegram_id=req.telegram_id,
            username=req.username,
            password=req.password,
        )
    except errors.AccountLockedError as exc:
        notif = NotificationService(db)
        notif.create(
            type=NotificationType.SECURITY,
            title="Блокировка входа через бота",
            body=f"Аккаунт {req.username} заблокирован",
            severity=Severity.CRITICAL,
            source="bot",
            metadata={"telegram_id": req.telegram_id, "locked_until": str(exc.locked_until)},
        )
        raise HTTPException(
            status_code=423,
            detail={"error": "locked", "locked_until": str(exc.locked_until)},
        )
    except errors.InvalidCredentialsError as exc:
        notif = NotificationService(db)
        notif.create(
            type=NotificationType.SECURITY,
            title="Неудачная попытка входа",
            body=f"Неверный пароль для {req.username}",
            severity=Severity.WARNING,
            source="bot",
            metadata={
                "telegram_id": req.telegram_id,
                "attempts_left": exc.attempts_left,
                "username": req.username,
            },
        )
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_password", "attempts_left": exc.attempts_left},
        )
    except errors.AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    notif = NotificationService(db)
    notif.create(
        type=NotificationType.AUDIT,
        title="Успешный вход через бота",
        body=f"Пользователь {req.username}",
        severity=Severity.INFO,
        source="bot",
        metadata={"telegram_id": req.telegram_id, "role": result["role"]},
    )

    return VerifyResponse(**result)


@router.post("/logout")
def logout(
    payload: dict = Depends(get_current_payload),
    db: Session = Depends(get_db),
) -> dict:
    api_auth = ApiAuthService(db)
    ok = api_auth.logout(payload["jti"])
    return {"ok": ok}


@router.get("/status", response_model=StatusResponse)
def status(payload: dict = Depends(get_current_payload)) -> StatusResponse:
    return StatusResponse(
        valid=True,
        telegram_id=payload.get("telegram_id"),
        role=payload.get("role"),
        expires_at=str(payload.get("exp")),
    )
