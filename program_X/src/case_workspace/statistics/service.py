"""Сервис статистики по делам."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from case_workspace.projects.models import Case, LocationStatus
from case_workspace.timetracking.service import TimeService


class StatsService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.time = TimeService(session)

    # --- сводные числа ---
    def summary(self) -> dict:
        today = date.today()

        total = self.session.scalar(select(func.count(Case.id))) or 0

        active = (
            self.session.scalar(
                select(func.count(Case.id)).where(
                    Case.location_status == LocationStatus.WITH_ME
                )
            )
            or 0
        )
        transferred = (
            self.session.scalar(
                select(func.count(Case.id)).where(
                    Case.location_status == LocationStatus.TRANSFERRED
                )
            )
            or 0
        )
        archived = (
            self.session.scalar(
                select(func.count(Case.id)).where(
                    Case.location_status == LocationStatus.ARCHIVED
                )
            )
            or 0
        )

        overdue = 0
        soon = 0
        mid = 0
        far = 0
        for c in self.session.scalars(
            select(Case).where(Case.location_status != LocationStatus.ARCHIVED)
        ):
            if c.current_deadline is None:
                continue
            days = (c.current_deadline - today).days
            if days < 0:
                overdue += 1
            elif days <= 14:
                soon += 1
            elif days <= 60:
                mid += 1
            else:
                far += 1

        totals = self.time.total_seconds_all_cases()
        total_seconds = sum(totals.values())

        return {
            "total": total,
            "active": active,
            "transferred": transferred,
            "archived": archived,
            "overdue": overdue,
            "soon": soon,
            "mid": mid,
            "far": far,
            "total_seconds": total_seconds,
        }

    # --- по статьям ---
    def cases_by_article(self) -> dict[str, int]:
        rows = self.session.execute(
            select(Case.article, func.count(Case.id))
            .where(Case.article != "")
            .group_by(Case.article)
            .order_by(func.count(Case.id).desc())
        ).all()
        return {article: count for article, count in rows}

    # --- по срочности ---
    def cases_by_urgency(self) -> dict[str, int]:
        today = date.today()
        result = {"Просрочено": 0, "≤ 14 дней": 0, "15–60 дней": 0, "> 60 дней": 0}
        for c in self.session.scalars(
            select(Case).where(Case.location_status != LocationStatus.ARCHIVED)
        ):
            if c.current_deadline is None:
                continue
            days = (c.current_deadline - today).days
            if days < 0:
                result["Просрочено"] += 1
            elif days <= 14:
                result["≤ 14 дней"] += 1
            elif days <= 60:
                result["15–60 дней"] += 1
            else:
                result["> 60 дней"] += 1
        return result

    # --- нагрузка по делам ---
    def load_by_case(self, limit: int = 20) -> list[tuple[str, int]]:
        totals = self.time.total_seconds_all_cases()
        rows: list[tuple[str, int]] = []
        for case_id, seconds in totals.items():
            if seconds <= 0:
                continue
            case = self.session.get(Case, case_id)
            if case is None:
                continue
            number = case.case_number or f"id{case_id}"
            rows.append((number, seconds))
        rows.sort(key=lambda r: r[1], reverse=True)
        return rows[:limit]

    # --- динамика по месяцам ---
    def cases_by_month(self, months: int = 12) -> list[tuple[str, int]]:
        """Последние N месяцев: [(YYYY-MM, count)]."""
        today = date.today()
        first_day = date(today.year, today.month, 1)
        boundaries: list[date] = []
        for _ in range(months):
            boundaries.append(first_day)
            first_day = (first_day - timedelta(days=1)).replace(day=1)
        boundaries.reverse()

        result: list[tuple[str, int]] = []
        all_cases = list(self.session.scalars(select(Case)))
        for i, start in enumerate(boundaries):
            end = boundaries[i + 1] if i + 1 < len(boundaries) else today + timedelta(days=1)
            count = sum(1 for c in all_cases if start <= c.initiated_at < end)
            result.append((start.strftime("%Y-%m"), count))
        return result
