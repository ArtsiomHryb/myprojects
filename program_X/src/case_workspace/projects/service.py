"""Сервис работы с делами."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from case_workspace.db.models import Role, UserAccount
from case_workspace.projects.models import (
    Case,
    CaseEvent,
    DeadlineExtension,
    EventType,
    LocationStatus,
)
from case_workspace.projects.validators import (
    add_months,
    build_case_number,
    parse_article,
    validate_parts,
)


class CaseService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_case(
        self,
        user: UserAccount,
        *,
        article: str,
        initiated_at: date,
        sequential_number: str,
        year: str | None = None,
        originating_agency: str | None = None,
        total_period_months: int = 2,
        parent_case_id: int | None = None,
        is_episode: bool = False,
        color_tag: str = "",
    ) -> Case:
        if year is None:
            year = str(initiated_at.year)[-2:]
        sequential = sequential_number.strip().zfill(4)

        if not is_episode:
            organ = (user.organ_code or "").strip()
            territorial = (user.territorial_code or "").strip()
            errors = validate_parts(year, organ, territorial, sequential)
            if errors:
                raise ValueError(" ".join(errors))
            case_number = build_case_number(year, organ, territorial, sequential)
            if self.session.scalar(select(Case).where(Case.case_number == case_number)):
                raise ValueError(f"Дело с номером {case_number} уже существует.")
        else:
            case_number = None

        deadline = add_months(initiated_at, total_period_months)
        code, part = parse_article(article)

        case = Case(
            case_number=case_number,
            year=year,
            sequential_number=sequential,
            article=article.strip(),
            article_code=code,
            article_part=part,
            initiated_at=initiated_at,
            current_deadline=deadline,
            total_period_months=total_period_months,
            originating_agency=originating_agency or (user.organization_name or ""),
            owner_id=user.id,
            parent_case_id=parent_case_id,
            is_episode=is_episode,
            color_tag=color_tag,
        )
        self.session.add(case)
        self.session.flush()
        self.session.add(CaseEvent(case_id=case.id, type=EventType.INITIATED, date=initiated_at))
        self.session.commit()
        self.ensure_position(case.id)
        return case

    def list_cases(
        self,
        user: UserAccount,
        *,
        include_archived: bool = False,
        show_all: bool | None = None,
    ) -> list[Case]:
        q = select(Case).where(Case.is_episode == False)  # noqa: E712
        if not include_archived:
            q = q.where(Case.location_status != LocationStatus.ARCHIVED)
        if show_all is None:
            show_all = user.role == Role.ADMIN
        if not show_all:
            q = q.where(Case.owner_id == user.id)
        q = q.order_by(Case.current_deadline.asc())
        return list(self.session.scalars(q))

    def get_case(self, case_id: int) -> Case | None:
        return self.session.get(Case, case_id)

    def extend_deadline(self, case_id: int, new_deadline: date, reason: str = "") -> Case:
        case = self.session.get(Case, case_id)
        if case is None:
            raise ValueError("Дело не найдено.")
        self.session.add(
            DeadlineExtension(
                case_id=case_id,
                old_deadline=case.current_deadline,
                new_deadline=new_deadline,
                reason=reason,
            )
        )
        case.current_deadline = new_deadline
        self.session.commit()
        return case

    def archive(self, case_id: int) -> Case:
        case = self.session.get(Case, case_id)
        if case is None:
            raise ValueError("Дело не найдено.")
        case.location_status = LocationStatus.ARCHIVED
        case.is_suspended = False
        self.session.commit()
        return case

    def unarchive(self, case_id: int) -> Case:
        case = self.session.get(Case, case_id)
        if case is None:
            raise ValueError("Дело не найдено.")
        case.location_status = LocationStatus.WITH_ME
        self.session.commit()
        return case

    def days_left(self, case: Case, today: date | None = None) -> int:
        today = today or date.today()
        return (case.current_deadline - today).days

    def create_episode(
        self,
        user: UserAccount,
        parent_case_id: int,
        *,
        article: str,
        initiated_at: date,
        total_period_months: int = 2,
    ) -> Case:
        parent = self.session.get(Case, parent_case_id)
        if parent is None:
            raise ValueError("Родительское дело не найдено.")
        return self.create_case(
            user,
            article=article,
            initiated_at=initiated_at,
            sequential_number="0000",
            total_period_months=total_period_months,
            parent_case_id=parent_case_id,
            is_episode=True,
        )
    # --- порядок на рабочем столе ---
    def get_desktop_order_map(self) -> dict[int, int]:
        from case_workspace.projects.models import CaseDesktopPosition

        rows = self.session.scalars(select(CaseDesktopPosition)).all()
        return {r.case_id: r.order_index for r in rows}

    def set_desktop_order(self, case_id: int, order_index: int) -> None:
        from case_workspace.projects.models import CaseDesktopPosition

        row = self.session.get(CaseDesktopPosition, case_id)
        if row is None:
            row = CaseDesktopPosition(case_id=case_id, order_index=order_index)
            self.session.add(row)
        else:
            row.order_index = order_index
        self.session.commit()

    def set_desktop_orders_bulk(self, pairs: list[tuple[int, int]]) -> None:
        from case_workspace.projects.models import CaseDesktopPosition

        for case_id, idx in pairs:
            row = self.session.get(CaseDesktopPosition, case_id)
            if row is None:
                self.session.add(
                    CaseDesktopPosition(case_id=case_id, order_index=idx)
                )
            else:
                row.order_index = idx
        self.session.commit()

    def reset_desktop_order(self) -> None:
        from case_workspace.projects.models import CaseDesktopPosition

        self.session.query(CaseDesktopPosition).delete()
        self.session.commit()

    def ensure_position(self, case_id: int) -> None:
        from case_workspace.projects.models import CaseDesktopPosition

        if self.session.get(CaseDesktopPosition, case_id) is None:
            max_idx = self.session.scalar(
                select(CaseDesktopPosition.order_index)
                .order_by(CaseDesktopPosition.order_index.desc())
                .limit(1)
            )
            next_idx = (max_idx or 0) + 1
            self.session.add(
                CaseDesktopPosition(case_id=case_id, order_index=next_idx)
            )
            self.session.commit()
