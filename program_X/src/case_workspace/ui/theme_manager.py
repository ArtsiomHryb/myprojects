"""Управление темой: светлая / тёмная / системная."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from case_workspace.ui.styles import DARK_QSS, LIGHT_QSS


class ThemeManager:
    def __init__(self) -> None:
        self._current = "light"

    @property
    def current(self) -> str:
        return self._current

    def apply(self, theme: str) -> None:
        app = QApplication.instance()
        if app is None:
            return
        if theme == "system":
            scheme = QGuiApplication.styleHints().colorScheme()
            theme = "dark" if scheme == Qt.ColorScheme.Dark else "light"
        self._current = theme
        app.setStyleSheet(DARK_QSS if theme == "dark" else LIGHT_QSS)

    def toggle(self) -> str:
        new = "dark" if self._current == "light" else "light"
        self.apply(new)
        return new


theme_manager = ThemeManager()
