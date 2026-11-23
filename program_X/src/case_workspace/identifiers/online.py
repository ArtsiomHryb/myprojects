"""Онлайн-резолверы: binlist.io, ipwho.is, ipapi.co."""

from __future__ import annotations

import requests

TIMEOUT = 5

HEADERS_BINLIST = {
    "Accept-Version": "3",
    "User-Agent": "CaseWorkspace/0.1 (+local)",
}


def resolve_card_online(bin_value: str) -> dict | None:
    """binlist.io — бесплатный API для BIN-справочника (6–8 цифр)."""
    digits = "".join(c for c in bin_value if c.isdigit())[:8]
    if len(digits) < 6:
        return None
    try:
        r = requests.get(
            f"https://lookup.binlist.net/{digits}",
            headers=HEADERS_BINLIST,
            timeout=TIMEOUT,
        )
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return None
    try:
        data = r.json()
    except ValueError:
        return None
    bank = data.get("bank") or {}
    country = data.get("country") or {}
    return {
        "source": "binlist.io",
        "scheme": data.get("scheme", ""),
        "card_type": data.get("type", ""),
        "brand": data.get("brand", ""),
        "prepaid": data.get("prepaid"),
        "bank_name": bank.get("name", ""),
        "country": country.get("alpha2", ""),
        "country_name": country.get("name", ""),
        "country_flag": country.get("emoji", ""),
    }


def _resolve_ipwhois(ip: str) -> dict | None:
    try:
        r = requests.get(f"https://ipwho.is/{ip}", timeout=TIMEOUT)
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return None
    try:
        data = r.json()
    except ValueError:
        return None
    if not data.get("success"):
        return None
    conn = data.get("connection") or {}
    tz = data.get("timezone") or {}
    return {
        "source": "ipwho.is",
        "country": data.get("country", ""),
        "country_code": data.get("country_code", ""),
        "region": data.get("region", ""),
        "city": data.get("city", ""),
        "postal": data.get("postal", ""),
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "isp": conn.get("isp", ""),
        "org": conn.get("org", ""),
        "asn": conn.get("asn"),
        "domain": conn.get("domain", ""),
        "timezone": tz.get("id", ""),
        "utc_offset": tz.get("utc", ""),
    }


def _resolve_ipapico(ip: str) -> dict | None:
    try:
        r = requests.get(f"https://ipapi.co/{ip}/json/", timeout=TIMEOUT)
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return None
    try:
        data = r.json()
    except ValueError:
        return None
    if data.get("error"):
        return None
    return {
        "source": "ipapi.co",
        "country": data.get("country_name", ""),
        "country_code": data.get("country_code", ""),
        "region": data.get("region", ""),
        "city": data.get("city", ""),
        "postal": data.get("postal", ""),
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "org": data.get("org", ""),
        "asn": data.get("asn", ""),
        "timezone": data.get("timezone", ""),
        "currency": data.get("currency", ""),
    }


def resolve_ip_online(ip: str) -> dict | None:
    """Комбинированный резолвер IP: ipwho.is + ipapi.co (два источника)."""
    first = _resolve_ipwhois(ip)
    second = _resolve_ipapico(ip)

    if first is None and second is None:
        return None

    primary = first or second
    sources = [s for s in [first, second] if s is not None]
    return {
        "sources": [s["source"] for s in sources],
        "country": primary.get("country", ""),
        "country_code": primary.get("country_code", ""),
        "region": primary.get("region", ""),
        "city": primary.get("city", ""),
        "postal": primary.get("postal", ""),
        "latitude": primary.get("latitude"),
        "longitude": primary.get("longitude"),
        "isp": primary.get("isp", ""),
        "org": primary.get("org", ""),
        "asn": primary.get("asn"),
        "timezone": primary.get("timezone", ""),
        "raw": sources,
    }
