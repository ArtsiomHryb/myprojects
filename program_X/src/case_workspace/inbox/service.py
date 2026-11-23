"""Сервис «Неразобранного»: анализ, гипотезы, привязка."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from case_workspace.inbox.entity_parser import extract_entities
from case_workspace.inbox.extractor import extract_text
from case_workspace.inbox.models import (
    InboxItem,
    InboxSource,
    InboxStatus,
)
from case_workspace.identifiers.validators import normalize
from case_workspace.participants.models import Party
from case_workspace.projects.models import Case


class InboxService:
    def __init__(self, session: Session) -> None:
        self.session = session

    # --- анализ ---
    def analyze_text(self, text: str) -> dict:
        entities = extract_entities(text)
        hypotheses = self._build_hypotheses(entities)
        tags = self._build_tags(entities)
        return {
            "entities": entities,
            "hypotheses": hypotheses,
            "auto_tags": tags,
        }

    def _build_hypotheses(self, entities: dict) -> list[dict]:
        """Гипотезы привязки к делам по номерам/ФИО/идентификаторам."""
        hypotheses: dict[int, dict] = {}

        # 1. По номерам дел (сильная)
        for case_number in entities.get("case_numbers", []):
            case = self.session.scalar(
                select(Case).where(Case.case_number == case_number)
            )
            if case:
                hid = case.id
                if hid not in hypotheses:
                    hypotheses[hid] = {
                        "case_id": case.id,
                        "case_number": case.case_number,
                        "weight": "strong",
                        "reasons": [],
                    }
                hypotheses[hid]["reasons"].append(f"номер дела {case_number}")

        # 2. По ФИО (сильная, если участник есть в деле)
        for name in entities.get("names", []):
            parties = list(
                self.session.scalars(select(Party).where(Party.full_name == name))
            )
            for p in parties:
                hid = p.case_id
                if hid not in hypotheses:
                    case = self.session.get(Case, p.case_id)
                    hypotheses[hid] = {
                        "case_id": p.case_id,
                        "case_number": case.case_number if case else "",
                        "weight": "strong",
                        "reasons": [],
                    }
                hypotheses[hid]["reasons"].append(f"ФИО {name}")

        # 3. По идентификаторам (средняя)
        # Используем локальные проверки IBAN/карт/телефонов/IP
        try:
            from case_workspace.identifiers.models import Identifier
            from case_workspace.identifiers.validators import detect_type

            all_values = (
                entities.get("cards", [])
                + entities.get("ibans", [])
                + entities.get("phones", [])
                + entities.get("ips", [])
            )
            for val in all_values:
                normalized = normalize(val)
                matches = list(
                    self.session.scalars(
                        select(Identifier).where(
                            Identifier.normalized_value == normalized
                        )
                    )
                )
                for m in matches:
                    hid = m.case_id
                    if hid not in hypotheses:
                        case = self.session.get(Case, m.case_id)
                        hypotheses[hid] = {
                            "case_id": m.case_id,
                            "case_number": case.case_number if case else "",
                            "weight": "medium",
                            "reasons": [],
                        }
                    hypotheses[hid]["reasons"].append(f"идентификатор {val}")
        except Exception:  # noqa: BLE001
            pass

        return list(hypotheses.values())

    def _build_tags(self, entities: dict) -> list[str]:
        tags: list[str] = []
        if entities.get("cards"):
            tags.append("#карта")
        if entities.get("ibans"):
            tags.append("#счёт")
        if entities.get("phones"):
            tags.append("#телефон")
        if entities.get("ips"):
            tags.append("#ip")
        if entities.get("case_numbers"):
            tags.append("#номер_дела")
        if entities.get("names"):
            tags.append("#ФИО")
        if not tags:
            tags.append("#не_распознано")
        return tags

    # --- CRUD ---
    def add_from_text(
        self, text: str, source: InboxSource = InboxSource.PROGRAM, source_file: str = ""
    ) -> InboxItem:
        if not text or not text.strip():
            raise ValueError("Текст пустой.")
        analysis = self.analyze_text(text)
        item = InboxItem(
            source=source,
            source_file=source_file,
            raw_text=text.strip(),
            extract_method="text",
            extracted_json=json.dumps(analysis["entities"], ensure_ascii=False),
            hypotheses_json=json.dumps(analysis["hypotheses"], ensure_ascii=False),
            auto_tags=",".join(analysis["auto_tags"]),
            status=InboxStatus.NEW,
        )
        self.session.add(item)
        self.session.commit()
        return item

    def add_from_file(self, path: Path) -> InboxItem:
        if not path.exists():
            raise ValueError(f"Файл не найден: {path}")
        result = extract_text(path)
        if result.error:
            raise ValueError(result.error)
        analysis = self.analyze_text(result.text)
        item = InboxItem(
            source=InboxSource.FILE,
            source_file=path.name,
            raw_text=result.text,
            extract_method=result.method,
            extracted_json=json.dumps(analysis["entities"], ensure_ascii=False),
            hypotheses_json=json.dumps(analysis["hypotheses"], ensure_ascii=False),
            auto_tags=",".join(analysis["auto_tags"]),
            status=InboxStatus.NEW,
        )
        self.session.add(item)
        self.session.commit()
        return item

    def list_items(self, status: InboxStatus | None = None) -> list[InboxItem]:
        q = select(InboxItem).order_by(InboxItem.received_at.desc())
        if status is not None:
            q = q.where(InboxItem.status == status)
        return list(self.session.scalars(q))

    def get(self, item_id: int) -> InboxItem | None:
        return self.session.get(InboxItem, item_id)

    def get_entities(self, item: InboxItem) -> dict:
        try:
            return json.loads(item.extracted_json) if item.extracted_json else {}
        except ValueError:
            return {}

    def get_hypotheses(self, item: InboxItem) -> list[dict]:
        try:
            return json.loads(item.hypotheses_json) if item.hypotheses_json else []
        except ValueError:
            return []

    def attach_to_case(self, item_id: int, case_id: int) -> InboxItem:
        item = self.session.get(InboxItem, item_id)
        if item is None:
            raise ValueError("Элемент не найден.")
        case = self.session.get(Case, case_id)
        if case is None:
            raise ValueError("Дело не найдено.")
        item.status = InboxStatus.ATTACHED
        item.attached_to_case_id = case_id
        item.reviewed_at = datetime.utcnow()
        self.session.commit()
        return item

    def ignore(self, item_id: int) -> InboxItem:
        item = self.session.get(InboxItem, item_id)
        if item is None:
            raise ValueError("Элемент не найден.")
        item.status = InboxStatus.IGNORED
        item.reviewed_at = datetime.utcnow()
        self.session.commit()
        return item

    def mark_reviewed(self, item_id: int) -> InboxItem:
        item = self.session.get(InboxItem, item_id)
        if item is None:
            raise ValueError("Элемент не найден.")
        item.status = InboxStatus.REVIEWED
        item.reviewed_at = datetime.utcnow()
        self.session.commit()
        return item

    def delete(self, item_id: int) -> None:
        item = self.session.get(InboxItem, item_id)
        if item:
            self.session.delete(item)
            self.session.commit()
