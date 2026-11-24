"""Гибридный сервис: локально + онлайн + кэш + статус."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from case_workspace.identifiers import local, online
from case_workspace.identifiers.models import (
    Identifier,
    IdentifierType,
    ResolverCache,
    VerificationStatus,
)
from case_workspace.identifiers.validators import (
    detect_type,
    luhn_check,
    normalize,
    validate_iban,
    validate_ip,
)


class IdentifierService:
    def __init__(self, session: Session) -> None:
        self.session = session

    # --- кэш ---
    def _get_cache(self, id_type: IdentifierType, value: str, source: str) -> dict | None:
        row = self.session.scalar(
            select(ResolverCache).where(
                ResolverCache.type == id_type,
                ResolverCache.normalized_value == value,
                ResolverCache.source == source,
            )
        )
        if row is None:
            return None
        age_days = (datetime.now(UTC) - row.fetched_at).days
        if age_days > row.ttl_days:
            return None
        try:
            return json.loads(row.result_json)
        except ValueError:
            return None

    def _set_cache(
        self, id_type: IdentifierType, value: str, source: str, result: dict, ttl_days: int
    ) -> None:
        row = self.session.scalar(
            select(ResolverCache).where(
                ResolverCache.type == id_type,
                ResolverCache.normalized_value == value,
                ResolverCache.source == source,
            )
        )
        payload = json.dumps(result, ensure_ascii=False)
        if row is None:
            self.session.add(
                ResolverCache(
                    type=id_type,
                    normalized_value=value,
                    source=source,
                    result_json=payload,
                    ttl_days=ttl_days,
                )
            )
        else:
            row.result_json = payload
            row.fetched_at = datetime.now(UTC)
            row.ttl_days = ttl_days
        self.session.commit()

    # --- резолв ---
    def resolve(self, value: str, use_online: bool = True) -> dict:
        v = normalize(value)
        id_type = detect_type(value)
        result: dict = {
            "type": id_type.value,
            "value": value,
            "normalized": v,
            "local": None,
            "online": None,
            "verification_status": VerificationStatus.UNKNOWN.value,
            "error": None,
        }

        if id_type == IdentifierType.OTHER:
            result["error"] = "Не удалось определить тип идентификатора."
            return result

        if id_type == IdentifierType.CARD and not luhn_check(v):
            result["error"] = "Некорректный номер карты (LUHN)."
        elif id_type == IdentifierType.IBAN and not validate_iban(v):
            result["error"] = "Некорректный IBAN (контрольная сумма)."
        elif id_type == IdentifierType.IP and not validate_ip(v):
            result["error"] = "Некорректный IP-адрес."

        result["local"] = local.resolve_local(self.session, id_type, value)

        if use_online:
            if id_type == IdentifierType.CARD:
                ttl = 90
                cached = self._get_cache(id_type, v, "binlist.io")
                if cached:
                    result["online"] = cached
                else:
                    fresh = online.resolve_card_online(value)
                    if fresh:
                        self._set_cache(id_type, v, "binlist.io", fresh, ttl)
                        result["online"] = fresh
            elif id_type == IdentifierType.IP:
                ttl = 7
                cached = self._get_cache(id_type, v, "ip_combined")
                if cached:
                    result["online"] = cached
                else:
                    fresh = online.resolve_ip_online(value)
                    if fresh:
                        self._set_cache(id_type, v, "ip_combined", fresh, ttl)
                        result["online"] = fresh

        result["verification_status"] = self._compute_status(
            id_type, result["local"], result["online"]
        ).value
        return result

    def _compute_status(
        self, id_type: IdentifierType, local_r: dict | None, online_r: dict | None
    ) -> VerificationStatus:
        if local_r is None and online_r is None:
            return VerificationStatus.UNKNOWN
        if local_r is None or online_r is None:
            return VerificationStatus.PARTIAL

        if id_type in (IdentifierType.CARD, IdentifierType.IBAN):
            lb = (local_r.get("bank_name") or "").lower()
            ob = (online_r.get("bank_name") or "").lower()
            if lb and ob:
                if lb == ob or lb in ob or ob in lb:
                    return VerificationStatus.CONFIRMED
                return VerificationStatus.CONFLICT
            return VerificationStatus.PARTIAL

        if id_type == IdentifierType.IP:
            lc = (local_r.get("country") or "").lower()[:2]
            oc = (online_r.get("country_code") or "").lower()[:2]
            if lc and oc and lc == oc:
                return VerificationStatus.CONFIRMED
            return VerificationStatus.PARTIAL

        return VerificationStatus.PARTIAL

    # --- CRUD ---
    def add(
        self,
        case_id: int,
        value: str,
        party_id: int | None = None,
        comment: str = "",
        use_online: bool = True,
    ) -> Identifier:
        v = normalize(value)
        id_type = detect_type(value)
        if id_type == IdentifierType.OTHER:
            raise ValueError("Не удалось определить тип идентификатора.")

        existing = self.session.scalar(
            select(Identifier).where(
                Identifier.case_id == case_id,
                Identifier.type == id_type,
                Identifier.normalized_value == v,
            )
        )
        if existing:
            raise ValueError(f"Этот идентификатор уже есть в деле (id={existing.id}).")

        result = self.resolve(value, use_online=use_online)
        ident = Identifier(
            case_id=case_id,
            party_id=party_id,
            type=id_type,
            value=value,
            normalized_value=v,
            resolved_local=(
                json.dumps(result["local"], ensure_ascii=False) if result["local"] else ""
            ),
            resolved_online=(
                json.dumps(result["online"], ensure_ascii=False) if result["online"] else ""
            ),
            verification_status=VerificationStatus(result["verification_status"]),
            verified_at=(
                datetime.now(UTC)
                if result["local"] or result["online"]
                else None
            ),
            comment=comment,
        )
        self.session.add(ident)
        self.session.commit()
        return ident

    def list_identifiers(self, case_id: int) -> list[Identifier]:
        return list(
            self.session.scalars(
                select(Identifier)
                .where(Identifier.case_id == case_id)
                .order_by(Identifier.type, Identifier.id)
            )
        )

    def delete(self, identifier_id: int) -> None:
        row = self.session.get(Identifier, identifier_id)
        if row:
            self.session.delete(row)
            self.session.commit()

    def search_across_cases(self, value: str) -> list[Identifier]:
        v = normalize(value)
        return list(
            self.session.scalars(
                select(Identifier).where(Identifier.normalized_value == v)
            )
        )
