"""Отслеживание бездействия: автоблокировка через N минут."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication


class IdleService(QObject):
    """Считает бездействие пользователя и сигналит блокировку."""

    block_required = Signal()

    def __init__(self, timeout_minutes: int = 15, parent=None) -> None:
        super().__init__(parent)
        self.timeout_ms = timeout_minutes * 60 * 1000
        self._enabled = True

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(self.timeout_ms)
        self._timer.timeout.connect(self._on_timeout)

        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def start(self) -> None:
        if self._enabled:
            self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if enabled:
            self._timer.start()
        else:
            self._timer.stop()

    def set_timeout_minutes(self, minutes: int) -> None:
        self.timeout_ms = minutes * 60 * 1000
        self._timer.setInterval(self.timeout_ms)
        if self._enabled:
            self._timer.start()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if self._enabled and self._timer.isActive():
            if event.type() in (
                QEvent.Type.MouseButtonPress,
                QEvent.Type.MouseMove,
                QEvent.Type.KeyPress,
                QEvent.Type.Wheel,
                QEvent.Type.TouchBegin,
            ):
                self._timer.start()
        return super().eventFilter(obj, event)

    def _on_timeout(self) -> None:
        self.block_required.emit()
