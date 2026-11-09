"""Окно входа."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from case_workspace.auth.service import AuthService
from case_workspace.db.models import UserAccount
from case_workspace.domain import errors


class LoginWindow(QWidget):
    def __init__(self, auth: AuthService, on_success: Callable[[UserAccount], None]) -> None:
        super().__init__()
        self.auth = auth
        self.on_success = on_success
        self._locked_until: datetime | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick_lock)

        self.setWindowTitle("Case Workspace — Вход")
        self.setMinimumSize(440, 340)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 32, 40, 32)
        root.setSpacing(12)

        title = QLabel("Вход в систему")
        title.setObjectName("h1")
        root.addWidget(title)

        form = QFormLayout()
        self.login = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.returnPressed.connect(self._on_login)
        form.addRow("Логин:", self.login)
        form.addRow("Пароль:", self.password)
        root.addLayout(form)

        self.status = QLabel("")
        self.status.setObjectName("danger")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        root.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.login_btn = QPushButton("Войти")
        self.login_btn.setObjectName("primary")
        self.login_btn.clicked.connect(self._on_login)
        btn_row.addWidget(self.login_btn)
        root.addLayout(btn_row)

    def _on_login(self) -> None:
        if not self.login_btn.isEnabled():
            return
        try:
            user = self.auth.authenticate(self.login.text(), self.password.text())
        except errors.InvalidCredentialsError as exc:
            self.status.setText(
                f"Неверный логин или пароль. Осталось попыток: {exc.attempts_left}"
            )
            return
        except errors.AccountLockedError as exc:
            self._start_lock(exc.locked_until)
            return
        except errors.AuthError as exc:
            self.status.setText(str(exc))
            return

        self.status.setText("")
        self._timer.stop()
        self.on_success(user)

    def _start_lock(self, locked_until: datetime) -> None:
        self._locked_until = locked_until
        self.login_btn.setEnabled(False)
        self._tick_lock()
        self._timer.start(1000)

    def _tick_lock(self) -> None:
        if self._locked_until is None:
            return
        now = datetime.utcnow()
        if now >= self._locked_until:
            self._timer.stop()
            self._locked_until = None
            self.login_btn.setEnabled(True)
            self.status.setText("Блокировка снята. Можно войти.")
            return
        remaining = int((self._locked_until - now).total_seconds())
        minutes, seconds = divmod(remaining, 60)
        self.status.setText(
            f"Учётная запись заблокирована. Повторите через {minutes}:{seconds:02d}"
        )