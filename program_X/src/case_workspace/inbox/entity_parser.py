"""Извлечение идентификаторов и сущностей из текста."""

from __future__ import annotations

import re

# Карта: 13-19 цифр, допускаются пробелы/дефисы между ними
CARD_RE = re.compile(r"\b(?:\d[\s\-]?){12,18}\d\b")

# IBAN РБ: BY + 2 цифры + 4 буквы + 20 цифр (группы по 4, пробелы допустимы)
IBAN_RE = re.compile(
    r"\bBY\d{2}\s?[A-Z]{4}(?:\s?\d{4}){5}\b", re.IGNORECASE
)

# Телефон РБ: +375 XX XXX-XX-XX (с любыми разделителями)
PHONE_RE = re.compile(r"\+375[\s\-()]?\d{2}[\s\-()]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}")

# IP: 4 группы цифр через точку
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

# Номер дела: ровно 11 цифр подряд
CASE_NUMBER_RE = re.compile(r"\b\d{11}\b")

# Паспорт РБ: 2 латинские буквы + 7 цифр
PASSPORT_RE = re.compile(r"\b[A-Z]{2}\d{7}\b")

# Дата: ДД.ММ.ГГГГ
DATE_RE = re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b")

# ФИО: 2-3 слова с заглавной буквы
NAME_RE = re.compile(r"\b[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2}\b")


def _empty() -> dict:
    return {
        "cards": [],
        "ibans": [],
        "phones": [],
        "ips": [],
        "case_numbers": [],
        "passports": [],
        "dates": [],
        "names": [],
    }


def _overlaps(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    """Проверяет, пересекается ли диапазон [start, end) с любым из spans."""
    for s, e in spans:
        if start < e and s < end:
            return True
    return False


def _validate_ip(value: str) -> bool:
    parts = value.split(".")
    if len(parts) != 4:
        return False
    return all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)


def _luhn_valid(card: str) -> bool:
    digits = [int(c) for c in card if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def extract_entities(text: str) -> dict:
    """Возвращает словарь извлечённых сущностей.

    Порядок обработки: от самых длинных паттернов к коротким,
    чтобы не было ложных срабатываний (IBAN содержит 20 цифр,
    часть из них могла бы выглядеть как номер карты).
    """
    if not text:
        return _empty()

    # 1. IBAN (самый длинный паттерн)
    iban_matches: list[tuple[int, int, str]] = []
    for m in IBAN_RE.finditer(text):
        iban_matches.append((m.start(), m.end(), m.group().strip()))
    iban_spans = [(s, e) for s, e, _ in iban_matches]
    ibans = [v for _, _, v in iban_matches]

    # 2. Телефоны (исключая пересечения с IBAN)
    phone_matches: list[tuple[int, int, str]] = []
    for m in PHONE_RE.finditer(text):
        if _overlaps(m.start(), m.end(), iban_spans):
            continue
        normalized = re.sub(r"[\s\-()]", "", m.group())
        phone_matches.append((m.start(), m.end(), normalized))
    phone_spans = [(s, e) for s, e, _ in phone_matches]
    phones = [v for _, _, v in phone_matches]

    # 3. IP (исключая IBAN и телефоны)
    ip_matches: list[tuple[int, int, str]] = []
    for m in IP_RE.finditer(text):
        if not _validate_ip(m.group()):
            continue
        if _overlaps(m.start(), m.end(), iban_spans + phone_spans):
            continue
        ip_matches.append((m.start(), m.end(), m.group()))
    ip_spans = [(s, e) for s, e, _ in ip_matches]
    ips = [v for _, _, v in ip_matches]

    # 4. Карты (исключая IBAN/телефоны/IP), только валидные по LUHN
    already_spans = iban_spans + phone_spans + ip_spans
    card_matches: list[tuple[int, int, str]] = []
    for m in CARD_RE.finditer(text):
        if _overlaps(m.start(), m.end(), already_spans):
            continue
        normalized = re.sub(r"[\s\-]", "", m.group())
        if not _luhn_valid(normalized):
            continue
        card_matches.append((m.start(), m.end(), normalized))
    card_spans = [(s, e) for s, e, _ in card_matches]
    cards = [v for _, _, v in card_matches]

    # 5. Номера дел (исключая пересечения со всем выше)
    all_used = iban_spans + phone_spans + ip_spans + card_spans
    case_numbers = [
        m.group()
        for m in CASE_NUMBER_RE.finditer(text)
        if not _overlaps(m.start(), m.end(), all_used)
    ]

    # 6. Паспорта
    passports = [m.group() for m in PASSPORT_RE.finditer(text)]

    # 7. Даты
    dates = [m.group() for m in DATE_RE.finditer(text)]

    # 8. ФИО (эвристика, только полные 2-3 слова)
    names: list[str] = []
    seen_names: set[str] = set()
    for m in NAME_RE.finditer(text):
        name = " ".join(m.group().split())
        if name not in seen_names:
            seen_names.add(name)
            names.append(name)

    return {
        "cards": cards,
        "ibans": ibans,
        "phones": phones,
        "ips": ips,
        "case_numbers": case_numbers,
        "passports": passports,
        "dates": dates,
        "names": names,
    }
