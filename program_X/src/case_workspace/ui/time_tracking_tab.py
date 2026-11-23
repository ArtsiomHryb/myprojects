"""Вкладка учёта времени в карточке дела."""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from case_workspace.timetracking.service import TimeService


class TimeTrackingTab(QWidget):
    def __init__(self, case_id: int, service: TimeService, parent=None) -> None:
        super().__init__(parent)
        self.case_id = case_id
        self.service = service
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._build()
        self._refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = QLabel("Учёт времени по делу")
        title.setObjectName("h1")
        root.addWidget(title)

        hint = QLabel(
            "Запустите таймер во время работы над делом. "
            "Можно вручную отредактировать накопленное время."
        )
        hint.setObjectName("caption")
        hint.setWordWrap(True)
        root.addWidget(hint)

        # Большой счётчик
        self.counter = QLabel("00:00:00")
        self.counter.setStyleSheet(
            "font-family: 'Menlo', monospace; font-size: 56px; "
            "font-weight: 600; color: #0F172A;"
        )
        self.counter.setAlignment(
            # Qt.AlignCenter через флаг
            __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.AlignmentFlag.AlignHCenter
        )
        root.addWidget(self.counter)

        # Состояние
        self.status = QLabel("⏹ остановлен")
        self.status.setStyleSheet("font-size: 14px; color: #64748B;")
        from PySide6.QtCore import Qt as _Qt

        self.status.setAlignment(_Qt.AlignmentFlag.AlignHCenter)
        root.addWidget(self.status)

        # Кнопки
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_start = QPushButton("▶ Старт")
        self.btn_start.setObjectName("primary")
        self.btn_start.setMinimumWidth(140)
        self.btn_start.setMinimumHeight(44)
        self.btn_start.clicked.connect(self._start)
        btn_row.addWidget(self.btn_start)

        self.btn_pause = QPushButton("⏸ Пауза")
        self.btn_pause.setMinimumWidth(140)
        self.btn_pause.setMinimumHeight(44)
        self.btn_pause.clicked.connect(self._pause)
        btn_row.addWidget(self.btn_pause)

        self.btn_stop = QPushButton("⏹ Стоп")
        self.btn_stop.setMinimumWidth(140)
        self.btn_stop.setMinimumHeight(44)
        self.btn_stop.clicked.connect(self._stop)
        btn_row.addWidget(self.btn_stop)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # Ручная правка
        manual_title = QLabel("Ручная корректировка:")
        manual_title.setStyleSheet("font-weight: 600; margin-top: 20px;")
        root.addWidget(manual_title)

        manual_row = QHBoxLayout()
        manual_row.addWidget(QLabel("Часов:"))
        self.hours_input = QLineEdit()
        self.hours_input.setPlaceholderText("0")
        self.hours_input.setMaximumWidth(80)
        manual_row.addWidget(self.hours_input)

        manual_row.addWidget(QLabel("Минут:"))
        self.minutes_input = QLineEdit()
        self.minutes_input.setPlaceholderText("0")
        self.minutes_input.setMaximumWidth(80)
        manual_row.addWidget(self.minutes_input)

        self.btn_apply = QPushButton("Применить")
        self.btn_apply.clicked.connect(self._apply_manual)
        manual_row.addWidget(self.btn_apply)
        manual_row.addStretch()
        root.addLayout(manual_row)

        # Инфо
        self.info = QLabel("")
        self.info.setObjectName("caption")
        self.info.setWordWrap(True)
        root.addWidget(self.info)

        root.addStretch()

    def _refresh(self) -> None:
        entry = self.service.get_running(self.case_id)
        if entry is None:
            # берём последнюю запись
            from sqlalchemy import select

            from case_workspace.timetracking.models import TimeEntry

            entry = self.service.session.scalar(
                select(TimeEntry)
                .where(TimeEntry.case_id == self.case_id)
                .order_by(TimeEntry.id.desc())
                .limit(1)
            )

        total = entry.total_seconds if entry else 0
        self._update_counter(total)

        if entry and entry.is_running:
            self.status.setText("▶ идёт")
            self.status.setStyleSheet("font-size: 14px; color: #16A34A; font-weight: 600;")
            self.btn_start.setEnabled(False)
            self.btn_pause.setEnabled(True)
            self.btn_stop.setEnabled(True)
            if not self._timer.isActive():
                self._timer.start(1000)
        else:
            self.status.setText("⏸ пауза" if entry and entry.accumulated_seconds else "⏹ остановлен")
            self.status.setStyleSheet("font-size: 14px; color: #64748B;")
            self.btn_start.setEnabled(True)
            self.btn_pause.setEnabled(False)
            self.btn_stop.setEnabled(False)
            if self._timer.isActive():
                self._timer.stop()

        if entry:
            hours = entry.total_seconds // 3600
            minutes = (entry.total_seconds % 3600) // 60
            self.info.setText(
                f"Всего по делу: {hours} ч {minutes:02d} мин "
                f"(записей: —, накоплено {entry.accumulated_seconds} с)"
            )
        else:
            self.info.setText("Записей пока нет.")

    def _tick(self) -> None:
        entry = self.service.get_running(self.case_id)
        if entry is None:
            self._timer.stop()
            return
        self._update_counter(entry.total_seconds)

    def _update_counter(self, seconds: int) -> None:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        self.counter.setText(f"{h:02d}:{m:02d}:{s:02d}")

    def _start(self) -> None:
        self.service.start(self.case_id)
        self._refresh()

    def _pause(self) -> None:
        self.service.pause(self.case_id)
        self._refresh()

    def _stop(self) -> None:
        self.service.stop(self.case_id)
        self._refresh()

    def _apply_manual(self) -> None:
        try:
            hours = int(self.hours_input.text() or 0)
            minutes = int(self.minutes_input.text() or 0)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Введите целые числа.")
            return
        if hours < 0 or minutes < 0 or minutes > 59:
            QMessageBox.warning(self, "Ошибка", "Часы >= 0, минуты 0-59.")
            return

        entry = self.service.get_or_create(self.case_id)
        total = hours * 3600 + minutes * 60
        try:
            self.service.set_manual_seconds(entry.id, total, note="ручная корректировка")
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        self._refresh()
        self.hours_input.clear()
        self.minutes_input.clear()
        QMessageBox.information(self, "Сохранено", f"Установлено: {hours} ч {minutes} мин.")
