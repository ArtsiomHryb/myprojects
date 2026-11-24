"""Экран блокировки: требует пароль для продолжения работы."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
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


class LockWindow(QWidget):
    unlocked = Signal()

    def __init__(self, auth: AuthService, user: UserAccount, parent=None) -> None:
        super().__init__(parent)
        self.auth = auth
        self.user = user
        self.setWindowTitle("Экран заблокирован")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setMinimumSize(480, 320)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(60, 50, 60, 50)
        root.setSpacing(14)

        title = QLabel("🔒 Программа заблокирована")
        title.setObjectName("h1")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        root.addWidget(title)

        hint = QLabel("Введите пароль для продолжения работы")
        hint.setObjectName("caption")
        hint.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        root.addWidget(hint)

        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Пароль")
        self.password.setMinimumHeight(40)
        self.password.returnPressed.connect(self._on_unlock)
        root.addWidget(self.password)

        self.status = QLabel("")
        self.status.setObjectName("danger")
        self.status.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        root.addWidget(self.status)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_unlock = QPushButton("Разблокировать")
        self.btn_unlock.setObjectName("primary")
        self.btn_unlock.setMinimumWidth(180)
        self.btn_unlock.setMinimumHeight(38)
        self.btn_unlock.clicked.connect(self._on_unlock)
        btn_row.addWidget(self.btn_unlock)
        btn_row.addStretch()
        root.addLayout(btn_row)

        root.addStretch()

        self.password.setFocus()

    def _on_unlock(self) -> None:
        pwd = self.password.text()
        if not pwd:
            self.status.setText("Введите пароль")
            return
        try:
            self.auth.authenticate(self.user.login, pwd)
        except errors.InvalidCredentialsError as exc:
            self.status.setText(
                f"Неверный пароль. Осталось: {exc.attempts_left}"
            )
            self.password.clear()
            return
        except errors.AccountLockedError as exc:
            self.status.setText(f"Заблокировано до {exc.locked_until:%H:%M:%S}")
            return
        except errors.AuthError as exc:
            self.status.setText(str(exc))
            return

        self.password.clear()
        self.status.setText("")
        self.unlocked.emit()
        self.close()

    def closeEvent(self, event) -> None:
        # Нельзя закрыть без разблокировки
        event.ignore()
