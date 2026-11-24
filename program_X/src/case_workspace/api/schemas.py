"""Pydantic-схемы API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class VerifyRequest(BaseModel):
    telegram_id: int
    username: str
    password: str


class VerifyResponse(BaseModel):
    token: str
    expires_at: str
    role: str
    user_id: int
    full_name: str


class StatusResponse(BaseModel):
    valid: bool
    telegram_id: int | None = None
    role: str | None = None
    expires_at: str | None = None


class CaseItem(BaseModel):
    id: int
    case_number: str | None = None
    article: str = ""
    initiated_at: str = ""
    current_deadline: str = ""
    days_left: int | None = None
    status: str = ""


class CaseDetail(CaseItem):
    originating_agency: str = ""
    accused_name: str = ""
    victim_name: str = ""
    parties: list[dict] = Field(default_factory=list)


class ResolveRequest(BaseModel):
    value: str


class DeadlineItem(BaseModel):
    case_id: int
    case_number: str | None = None
    article: str = ""
    current_deadline: str = ""
    days_left: int = 0


class NotificationItem(BaseModel):
    id: int
    type: str
    severity: str
    title: str
    body: str
    created_at: str
    read_at: str | None = None
    metadata: dict = Field(default_factory=dict)
