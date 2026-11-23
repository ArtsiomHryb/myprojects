"""Окно тайминга: таблица всех дел с цветовой шкалой срочности."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QTimer
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from case_workspace.db.models import UserAccount
from case_workspace.projects.models import LocationStatus
from case_workspace.projects.service import CaseService
from case_workspace.timetracking.service import TimeService


def urgency_color(days: int | None) -> str:
    if days is None:
        return "#94A3B8"
    if days < 0:
        return "#991B1B"
    if days <= 14:
        return "#DC2626"
    if days <= 30:
        return "#EA580C"
    if days <= 60:
        return "#CA8A04"
    return "#16A34A"


class TimelineWindow(QWidget):
    def __init__(
        self,
        user: UserAccount,
        case_service: CaseService,
        time_service: TimeService,
        on_open_case=None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.user = user
        self.cases = case_service
        self.time = time_service
        self.on_open_case = on_open_case
        self._ids: list[int] = []

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(30_000)

        self.setWindowTitle("Тайминг")
        self.setMinimumSize(1100, 700)
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Тайминг по делам")
        title.setObjectName("h1")
        header.addWidget(title)
        header.addStretch()
        self.btn_refresh = QPushButton("Обновить")
        self.btn_refresh.clicked.connect(self.refresh)
        header.addWidget(self.btn_refresh)
        root.addLayout(header)

        filters = QHBoxLayout()
        filters.addWidget(QLabel("Фильтр:"))
        self.filter_status = QComboBox()
        self.filter_status.addItem("Активные", "active")
        self.filter_status.addItem("Все (без архива)", "all")
        self.filter_status.addItem("Приостановленные", "suspended")
        self.filter_status.addItem("Архив", "archived")
        self.filter_status.currentIndexChanged.connect(self.refresh)
        filters.addWidget(self.filter_status)
        filters.addStretch()
        self.summary = QLabel("")
        self.summary.setObjectName("caption")
        filters.addWidget(self.summary)
        root.addLayout(filters)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["", "Номер", "Статья", "Обвиняемый", "Часы", "Срок до", "Осталось", "Статус"]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._open_selected)
        root.addWidget(self.table, 1)

        hint = QLabel(
            "Сортировка по срочности: сверху — дела с наименьшим остатком времени. "
            "Обновление раз в 30 секунд."
        )
        hint.setObjectName("caption")
        hint.setWordWrap(True)
        root.addWidget(hint)

    def refresh(self) -> None:
        mode = self.filter_status.currentData()
        all_cases = self.cases.list_cases(self.user, include_archived=True)

        if mode == "active":
            filtered = [
                c
                for c in all_cases
                if c.location_status != LocationStatus.ARCHIVED
                and not getattr(c, "is_suspended", False)
            ]
        elif mode == "suspended":
            filtered = [c for c in all_cases if getattr(c, "is_suspended", False)]
        elif mode == "archived":
            filtered = [
                c for c in all_cases if c.location_status == LocationStatus.ARCHIVED
            ]
        else:
            filtered = [
                c for c in all_cases if c.location_status != LocationStatus.ARCHIVED
            ]

        totals = self.time.total_seconds_all_cases()
        today = date.today()

        rows: list[tuple] = []
        for c in filtered:
            days = (c.current_deadline - today).days if c.current_deadline else None
            seconds = totals.get(c.id, 0)
            rows.append((c, days, seconds))

        rows.sort(key=lambda r: (r[1] is None, r[1] if r[1] is not None else 0))

        self.table.setRowCount(len(rows))
        for row, (c, days, seconds) in enumerate(rows):
            color = urgency_color(days)
            dot = QTableWidgetItem("●")
            dot.setForeground(QBrush(QColor(color)))
            self.table.setItem(row, 0, dot)

            self.table.setItem(row, 1, QTableWidgetItem(c.case_number or "—"))
            self.table.setItem(row, 2, QTableWidgetItem(c.article or "—"))
            self.table.setItem(row, 3, QTableWidgetItem(c.accused_name or "—"))

            if seconds > 0:
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                hours_text = f"{hours} ч {minutes:02d} мин"
            else:
                hours_text = "—"
            self.table.setItem(row, 4, QTableWidgetItem(hours_text))

            deadline_text = (
                c.current_deadline.strftime("%d.%m.%Y") if c.current_deadline else "—"
            )
            self.table.setItem(row, 5, QTableWidgetItem(deadline_text))

            if days is None:
                days_text = "—"
            elif days < 0:
                days_text = f"просрочено {abs(days)} дн."
            elif days == 0:
                days_text = "сегодня"
            else:
                days_text = f"{days} дн."
            days_item = QTableWidgetItem(days_text)
            days_item.setForeground(QBrush(QColor(color)))
            self.table.setItem(row, 6, days_item)

            if getattr(c, "is_suspended", False):
                status = "⏸ приостановлено"
            elif c.location_status == LocationStatus.ARCHIVED:
                status = "🗄 архив"
            elif c.location_status == LocationStatus.TRANSFERRED:
                status = "→ передано"
            else:
                status = "активно"
            self.table.setItem(row, 7, QTableWidgetItem(status))

        self._ids = [c.id for c, _, _ in rows]
        self.summary.setText(f"Дел: {len(rows)}")

    def _open_selected(self) -> None:
        if self.on_open_case is None:
            return
        row = self.table.currentRow()
        if row < 0 or row >= len(self._ids):
            return
        self.on_open_case(self._ids[row])
