"""Валидация номеров, сроков, статей."""

import calendar
import re
from datetime import date


def add_months(d: date, months: int) -> date:
    """Прибавляет N календарных месяцев (01.01 + 2 → 01.03)."""
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return date(y, m, day)


def parse_article(article: str) -> tuple[str, str]:
    """'205 ч.2' → ('205','2'), 'ст. 205' → ('205','')."""
    m = re.search(r"(\d+)(?:\s*ч\.?\s*(\d+))?", article or "")
    if not m:
        return ((article or "").strip(), "")
    return (m.group(1), m.group(2) or "")


def build_case_number(year: str, organ: str, territorial: str, sequential: str) -> str:
    return f"{year}{organ}{territorial}{sequential.zfill(4)}"


def validate_parts(year: str, organ: str, territorial: str, sequential: str) -> list[str]:
    errors: list[str] = []
    if not (year.isdigit() and len(year) == 2):
        errors.append("Год — 2 цифры.")
    if not (organ.isdigit() and len(organ) == 2):
        errors.append("Код органа — 2 цифры (задаётся в профиле).")
    if not (territorial.isdigit() and len(territorial) == 3):
        errors.append("Территориальный код — 3 цифры (задаётся в профиле).")
    if not (sequential.isdigit() and 1 <= len(sequential) <= 4):
        errors.append("Порядковый номер — 1–4 цифры.")
    return errors