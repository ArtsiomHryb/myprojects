"""Сервис календаря: события + дедлайны дел."""

from __future__ import annotations

import calendar as cal
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from case_workspace.calendar.models import CalendarEvent, EventType
from case_workspace.projects.models import Case, LocationStatus


class CalendarService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_event(
        self,
        event_date: date,
        title: str,
        event_type: EventType = EventType.REMINDER,
        case_id: int | None = None,
        description: str = "",
    ) -> CalendarEvent:
        if not title.strip():
            raise ValueError("Укажите название события.")
        ev = CalendarEvent(
            case_id=case_id,
            event_date=event_date,
            type=event_type,
            title=title.strip(),
            description=description.strip(),
        )
        self.session.add(ev)
        self.session.commit()
        return ev

    def list_events(
        self, from_date: date, to_date: date, include_done: bool = True
    ) -> list[CalendarEvent]:
        q = select(CalendarEvent).where(
            CalendarEvent.event_date >= from_date,
            CalendarEvent.event_date <= to_date,
        )
        if not include_done:
            q = q.where(CalendarEvent.done == False)  # noqa: E712
        q = q.order_by(CalendarEvent.event_date, CalendarEvent.id)
        return list(self.session.scalars(q))

    def toggle_done(self, event_id: int) -> CalendarEvent | None:
        ev = self.session.get(CalendarEvent, event_id)
        if ev is None:
            return None
        ev.done = not ev.done
        self.session.commit()
        return ev

    def delete_event(self, event_id: int) -> None:
        ev = self.session.get(CalendarEvent, event_id)
        if ev:
            self.session.delete(ev)
            self.session.commit()

    def deadlines_in_range(
        self, from_date: date, to_date: date, include_archived: bool = False
    ) -> list[Case]:
        q = select(Case).where(
            Case.current_deadline >= from_date,
            Case.current_deadline <= to_date,
        )
        if not include_archived:
            q = q.where(Case.location_status != LocationStatus.ARCHIVED)
        q = q.order_by(Case.current_deadline)
        return list(self.session.scalars(q))

    def month_overview(self, year: int, month: int) -> dict:
        first = date(year, month, 1)
        last_day = cal.monthrange(year, month)[1]
        last = date(year, month, last_day)

        events = self.list_events(first, last)
        deadlines = self.deadlines_in_range(first, last)

        by_day_events: dict[date, list[CalendarEvent]] = {}
        for ev in events:
            by_day_events.setdefault(ev.event_date, []).append(ev)

        by_day_deadlines: dict[date, list[Case]] = {}
        for c in deadlines:
            if c.current_deadline is None:
                continue
            by_day_deadlines.setdefault(c.current_deadline, []).append(c)

        return {
            "first": first,
            "last": last,
            "events_by_day": by_day_events,
            "deadlines_by_day": by_day_deadlines,
            "total_events": len(events),
            "total_deadlines": len(deadlines),
        }
