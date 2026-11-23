"""Определение типа и валидация идентификаторов."""

from __future__ import annotations

import re

from case_workspace.identifiers.models import IdentifierType

_CARD_RE = re.compile(r"\b\d{13,19}\b")
_IBAN_RE = re.compile(r"\bBY\d{2}[A-Z]{4}\d{20}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"\+375\d{9}\b")
_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def normalize(value: str) -> str:
    return re.sub(r"[\s\-()]+", "", value.strip())


def detect_type(value: str) -> IdentifierType:
    v = normalize(value).upper() if value.upper().startswith("BY") else normalize(value)
    if _IBAN_RE.fullmatch(v):
        return IdentifierType.IBAN
    if _PHONE_RE.fullmatch(v):
        return IdentifierType.PHONE
    if _CARD_RE.fullmatch(v):
        return IdentifierType.CARD
    if _IP_RE.fullmatch(v):
        return IdentifierType.IP
    return IdentifierType.OTHER


def luhn_check(card: str) -> bool:
    digits = [int(c) for c in card if c.isdigit()]
    if not digits:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def validate_iban(value: str) -> bool:
    v = normalize(value).upper()
    if not _IBAN_RE.fullmatch(v):
        return False
    rearranged = v[4:] + v[:4]
    numeric = "".join(str(int(c, 36)) for c in rearranged)
    return int(numeric) % 97 == 1


def validate_ip(value: str) -> bool:
    v = normalize(value)
    if not _IP_RE.fullmatch(v):
        return False
    parts = v.split(".")
    return all(0 <= int(p) <= 255 for p in parts)
