"""JWT-сервис для API бота."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from case_workspace.auth_api.models import SessionToken
from case_workspace.auth.service import AuthService
from case_workspace.db.models import UserAccount
from case_workspace.utils.time import utc_now

JWT_SECRET_KEY = "case_workspace_local_secret_change_me"  # в проде — из keyring
JWT_ALGORITHM = "HS256"
TOKEN_TTL_HOURS = 24


class ApiAuthService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.auth = AuthService(session)

    def login_with_password(
        self,
        telegram_id: int,
        username: str,
        password: str,
    ) -> dict:
        """Проверяет пароль через существующий AuthService.

        Возвращает {token, expires_at, role} или бросает исключение.
        """
        user: UserAccount = self.auth.authenticate(username, password)

        jti = secrets.token_urlsafe(32)
        expires_at = utc_now() + timedelta(hours=TOKEN_TTL_HOURS)

        payload = {
            "sub": str(user.id),
            "jti": jti,
            "role": user.role.value,
            "telegram_id": telegram_id,
            "exp": expires_at,
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

        st = SessionToken(
            telegram_id=telegram_id,
            username=username,
            jti=jti,
            role=user.role.value,
            expires_at=expires_at,
        )
        self.session.add(st)
        self.session.commit()

        return {
            "token": token,
            "expires_at": expires_at.isoformat(),
            "role": user.role.value,
            "user_id": user.id,
            "full_name": user.full_name,
        }

    def verify_token(self, token: str) -> dict | None:
        """Возвращает payload или None, если токен невалиден/отозван."""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

        jti = payload.get("jti")
        if not jti:
            return None

        st = self.session.scalar(
            select(SessionToken).where(SessionToken.jti == jti)
        )
        if st is None or st.revoked_at is not None:
            return None

        st.last_activity = utc_now()
        self.session.commit()
        return payload

    def logout(self, jti: str) -> bool:
        st = self.session.scalar(select(SessionToken).where(SessionToken.jti == jti))
        if st is None:
            return False
        st.revoked_at = utc_now()
        self.session.commit()
        return True

    def revoke_all_for_telegram_id(self, telegram_id: int) -> int:
        rows = list(
            self.session.scalars(
                select(SessionToken).where(
                    SessionToken.telegram_id == telegram_id,
                    SessionToken.revoked_at == None,  # noqa: E712
                )
            )
        )
        count = 0
        now = utc_now()
        for st in rows:
            st.revoked_at = now
            count += 1
        self.session.commit()
        return count
