"""Сервис работы с участниками."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from case_workspace.participants.models import Party, PartyRole


class PartyService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_party(
        self,
        case_id: int,
        *,
        role: PartyRole,
        full_name: str,
        birth_date: date | None = None,
        registration_address: str = "",
        residence_address: str = "",
        passport_id: str = "",
        contact_phone: str = "",
        comment: str = "",
    ) -> Party:
        if not full_name.strip():
            raise ValueError("ФИО обязательно.")
        party = Party(
            case_id=case_id,
            role=role,
            full_name=full_name.strip(),
            birth_date=birth_date,
            registration_address=registration_address.strip(),
            residence_address=residence_address.strip(),
            passport_id=passport_id.strip(),
            contact_phone=contact_phone.strip(),
            comment=comment.strip(),
        )
        self.session.add(party)
        self.session.commit()
        return party

    def list_parties(self, case_id: int) -> list[Party]:
        return list(
            self.session.scalars(
                select(Party)
                .where(Party.case_id == case_id)
                .order_by(Party.role, Party.full_name)
            )
        )

    def delete_party(self, party_id: int) -> None:
        party = self.session.get(Party, party_id)
        if party is not None:
            self.session.delete(party)
            self.session.commit()