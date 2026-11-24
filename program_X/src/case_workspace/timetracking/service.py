"""Сервис учёта времени."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from case_workspace.timetracking.models import TimeEntry
from case_workspace.utils.time import utc_now


def _fmt_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h} ч {m:02d} мин"
    if m > 0:
        return f"{m} мин {s:02d} с"
    return f"{s} с"


class TimeService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_running(self, case_id: int) -> TimeEntry | None:
        return self.session.scalar(
            select(TimeEntry).where(
                TimeEntry.case_id == case_id, TimeEntry.is_running == True  # noqa: E712
            )
        )

    def get_or_create(self, case_id: int) -> TimeEntry:
        entry = self.get_running(case_id)
        if entry is not None:
            return entry
        last = self.session.scalar(
            select(TimeEntry)
            .where(TimeEntry.case_id == case_id)
            .order_by(TimeEntry.id.desc())
            .limit(1)
        )
        if last is not None and not last.is_running:
            return last
        entry = TimeEntry(case_id=case_id, is_running=False, accumulated_seconds=0)
        self.session.add(entry)
        self.session.commit()
        return entry

    def start(self, case_id: int) -> TimeEntry:
        running = self.get_running(case_id)
        if running is not None:
            return running
        entry = self.get_or_create(case_id)
        entry.is_running = True
        entry.started_at = utc_now()
        self.session.commit()
        return entry

    def pause(self, case_id: int) -> TimeEntry | None:
        running = self.get_running(case_id)
        if running is None:
            return None
        if running.started_at:
            running.accumulated_seconds += int(
                (utc_now() - running.started_at).total_seconds()
            )
        running.is_running = False
        running.started_at = None
        self.session.commit()
        return running

    def stop(self, case_id: int) -> TimeEntry | None:
        return self.pause(case_id)

    def set_manual_seconds(self, entry_id: int, seconds: int, note: str = "") -> TimeEntry:
        entry = self.session.get(TimeEntry, entry_id)
        if entry is None:
            raise ValueError("Запись не найдена.")
        entry.is_running = False
        entry.started_at = None
        entry.accumulated_seconds = max(0, int(seconds))
        entry.manual_override = True
        entry.note = note.strip()
        self.session.commit()
        return entry

    def total_seconds_for_case(self, case_id: int) -> int:
        entries = list(
            self.session.scalars(select(TimeEntry).where(TimeEntry.case_id == case_id))
        )
        return sum(e.total_seconds for e in entries)

    def total_seconds_all_cases(self) -> dict[int, int]:
        rows = self.session.execute(
            select(
                TimeEntry.case_id,
                func.coalesce(func.sum(TimeEntry.accumulated_seconds), 0),
            ).group_by(TimeEntry.case_id)
        ).all()
        result: dict[int, int] = {cid: int(total) for cid, total in rows}

        running_entries = list(
            self.session.scalars(
                select(TimeEntry).where(TimeEntry.is_running == True)  # noqa: E712
            )
        )
        for e in running_entries:
            result[e.case_id] = result.get(e.case_id, 0) + e.total_seconds
        return result

    @staticmethod
    def fmt(seconds: int) -> str:
        return _fmt_duration(seconds)
