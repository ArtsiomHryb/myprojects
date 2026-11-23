"""Локальные справочники: IBAN-коды банков РБ, BIN-диапазоны, телефоны."""

from __future__ import annotations

import phonenumbers
from phonenumbers import carrier
from sqlalchemy import select
from sqlalchemy.orm import Session

from case_workspace.identifiers.models import BankCode, BinRange, IdentifierType
from case_workspace.identifiers.validators import normalize

SEED_BANK_CODES: dict[str, tuple[str, str]] = {
    "AKBB": ("ОАО «Сберегательный банк «Беларусбанк»", "AKBBBY2X"),
    "BAPB": ("ОАО «Белагропромбанк»", "BAPBBY2X"),
    "BLBB": ("ОАО «Белинвестбанк»", "BLBBBY2X"),
    "MMBN": ("ОАО «Банк Дабрабыт»", "MMBNBY22"),
    "POIS": ("ОАО «Паритетбанк»", "POISBY2X"),
    "BPSB": ("ОАО «Сбер Банк»", "BPSBBY2X"),
    "OLMP": ("ОАО «Белгазпромбанк»", "OLMPBY2X"),
    "ALFA": ("ЗАО «Альфа-Банк»", "ALFABY2X"),
    "TECN": ("ОАО «Технобанк»", "TECNBY22"),
    "UNBS": ("ОАО «БНБ-Банк»", "UNBSBY2X"),
    "MTBK": ("ЗАО «МТБанк»", "MTBKBY2X"),
    "IRJS": ("ОАО «Банк ВТБ (Беларусь)»", "IRJSBY2X"),
    "GTBN": ("ОАО «Банк БелВЭБ»", "GTBNBY2X"),
    "SLAN": ("ОАО «Банк «Славия»", "SLANBY2X"),
    "REDJ": ("ОАО «Белорусский народный банк»", "REDJBY2X"),
    "ICBC": ("ЗАО «Банк «РРБ-Банк»", "ICBCBY2X"),
}

SEED_BIN_RANGES: list[tuple[str, str, str, str, str, str]] = [
    ("911200", "911299", "Belkart", "debit", "ОАО «АСБ Беларусбанк»", "BY"),
    ("9112000", "9112009", "Belkart", "debit", "ОАО «АСБ Беларусбанк»", "BY"),
    ("911201", "911201", "Belkart", "debit", "ОАО «Белагропромбанк»", "BY"),
    ("427600", "427699", "Visa", "credit", "ОАО «АСБ Беларусбанк»", "BY"),
    ("456789", "456789", "Visa", "debit", "ОАО «Белагропромбанк»", "BY"),
]


def seed_local_tables(session: Session) -> None:
    if session.scalar(select(BankCode.id).limit(1)) is None:
        for code, (name, bic) in SEED_BANK_CODES.items():
            session.add(BankCode(code=code, bank_name=name, bic=bic, country="BY"))
    if session.scalar(select(BinRange.id).limit(1)) is None:
        for start, end, scheme, ctype, bank, country in SEED_BIN_RANGES:
            session.add(
                BinRange(
                    bin_start=start,
                    bin_end=end,
                    scheme=scheme,
                    card_type=ctype,
                    bank_name=bank,
                    country=country,
                )
            )
    session.commit()


def resolve_iban_local(session: Session, value: str) -> dict | None:
    v = normalize(value).upper()
    if len(v) < 8 or not v.startswith("BY"):
        return None
    bank_code = v[4:8]
    bank = session.scalar(select(BankCode).where(BankCode.code == bank_code))
    if bank is None:
        return None
    return {
        "source": "local_iban",
        "bank_code": bank.code,
        "bank_name": bank.bank_name,
        "bic": bank.bic,
        "country": bank.country,
    }


def resolve_card_local(session: Session, value: str) -> dict | None:
    v = normalize(value)
    if len(v) < 6:
        return None
    prefix6 = v[:6]
    prefix8 = v[:8] if len(v) >= 8 else prefix6
    rows = list(session.scalars(select(BinRange)))
    best = None
    for row in rows:
        if row.bin_start <= prefix8 and (row.bin_end == "" or row.bin_end >= prefix8):
            if best is None or len(row.bin_start) > len(best.bin_start):
                best = row
        elif row.bin_start <= prefix6 and (row.bin_end == "" or row.bin_end >= prefix6):
            if best is None:
                best = row
    if best is None:
        return None
    return {
        "source": "local_bin",
        "scheme": best.scheme,
        "card_type": best.card_type,
        "bank_name": best.bank_name,
        "country": best.country,
    }


def resolve_phone_local(value: str) -> dict | None:
    v = normalize(value)
    try:
        number = phonenumbers.parse(v, "BY")
    except phonenumbers.NumberParseException:
        return None
    if not phonenumbers.is_valid_number(number):
        return None
    carrier_name = carrier.name_for_number(number, "ru")
    region = phonenumbers.region_code_for_number(number)
    return {
        "source": "local_phone",
        "valid": True,
        "country": region or "BY",
        "carrier": carrier_name or "неизвестен",
        "national": phonenumbers.format_number(
            number, phonenumbers.PhoneNumberFormat.NATIONAL
        ),
        "international": phonenumbers.format_number(
            number, phonenumbers.PhoneNumberFormat.INTERNATIONAL
        ),
    }


def resolve_local(session: Session, id_type: IdentifierType, value: str) -> dict | None:
    if id_type == IdentifierType.IBAN:
        return resolve_iban_local(session, value)
    if id_type == IdentifierType.CARD:
        return resolve_card_local(session, value)
    if id_type == IdentifierType.PHONE:
        return resolve_phone_local(value)
    return None
