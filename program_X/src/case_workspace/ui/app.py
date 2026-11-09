"""Точка сборки UI и зависимостей."""

from __future__ import annotations

import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from case_workspace.auth.service import AuthService
from case_workspace.db.base import init_db, session_factory
from case_workspace.db.models import UserAccount
from case_workspace.logging_setup import setup_logging
from case_workspace.ui.login_window import LoginWindow
from case_workspace.ui.main_window import MainWindow
from case_workspace.ui.register_window import RegisterWindow
from case_workspace.ui.styles import LIGHT_QSS


class Application:
    def __init__(self) -> None:
        setup_logging()

        self.qt_app = QApplication(sys.argv)
        self.qt_app.setApplicationName("Case Workspace")
        self.qt_app.setStyle("Fusion")
        self.qt_app.setFont(QFont("Inter", 10))
        self.qt_app.setStyleSheet(LIGHT_QSS)

        self.engine = init_db()
        self.Session = session_factory(self.engine)

        self.login_window: LoginWindow | None = None
        self.register_window: RegisterWindow | None = None
        self.main_window: MainWindow | None = None

        self._show_entry()

    def _show_entry(self) -> None:
        with self.Session() as session:
            auth = AuthService(session)
            if auth.has_users():
                self.login_window = LoginWindow(auth, self._on_login_success)
                self.login_window.show()
            else:
                self.register_window = RegisterWindow(auth, self._on_login_success)
                self.register_window.show()

    def _on_login_success(self, user: UserAccount) -> None:
        self.main_window = MainWindow(user)
        self.main_window.show()
        if self.login_window is not None:
            self.login_window.close()
            self.login_window = None
        if self.register_window is not None:
            self.register_window.close()
            self.register_window = None

    def run(self) -> int:
        return self.qt_app.exec()