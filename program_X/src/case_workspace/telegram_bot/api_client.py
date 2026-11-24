"""HTTP-клиент к локальному API."""

from __future__ import annotations

import httpx

from case_workspace.telegram_bot.config import API_URL

TIMEOUT = 15


class ApiError(Exception):
    def __init__(self, status_code: int, detail) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API {status_code}: {detail}")


def _headers(token: str | None) -> dict:
    return {"Authorization": f"Bearer {token}"} if token else {}


def verify(telegram_id: int, username: str, password: str) -> dict:
    try:
        r = httpx.post(
            f"{API_URL}/auth/verify",
            json={"telegram_id": telegram_id, "username": username, "password": password},
            timeout=TIMEOUT,
        )
    except httpx.RequestError as exc:
        raise ApiError(0, f"API недоступен: {exc}") from exc
    if r.status_code == 200:
        return r.json()
    try:
        detail = r.json().get("detail", "")
    except Exception:
        detail = r.text
    raise ApiError(r.status_code, detail)


def logout(token: str) -> dict:
    try:
        r = httpx.post(f"{API_URL}/auth/logout", headers=_headers(token), timeout=TIMEOUT)
    except httpx.RequestError:
        return {"ok": False}
    return r.json() if r.status_code == 200 else {"ok": False}


def list_cases(token: str) -> list[dict]:
    try:
        r = httpx.get(f"{API_URL}/cases", headers=_headers(token), timeout=TIMEOUT)
    except httpx.RequestError as exc:
        raise ApiError(0, str(exc)) from exc
    if r.status_code == 200:
        return r.json()
    raise ApiError(r.status_code, r.text)


def get_case(token: str, case_number: str) -> dict:
    try:
        r = httpx.get(f"{API_URL}/cases/{case_number}", headers=_headers(token), timeout=TIMEOUT)
    except httpx.RequestError as exc:
        raise ApiError(0, str(exc)) from exc
    if r.status_code == 200:
        return r.json()
    raise ApiError(r.status_code, r.text)


def list_deadlines(token: str, days: int = 30) -> list[dict]:
    try:
        r = httpx.get(
            f"{API_URL}/deadlines", params={"days": days}, headers=_headers(token), timeout=TIMEOUT
        )
    except httpx.RequestError as exc:
        raise ApiError(0, str(exc)) from exc
    if r.status_code == 200:
        return r.json()
    raise ApiError(r.status_code, r.text)


def resolve_identifier(token: str, value: str) -> dict:
    try:
        r = httpx.post(
            f"{API_URL}/identifiers/resolve",
            json={"value": value},
            headers=_headers(token), timeout=TIMEOUT,
        )
    except httpx.RequestError as exc:
        raise ApiError(0, str(exc)) from exc
    if r.status_code == 200:
        return r.json()
    raise ApiError(r.status_code, r.text)
