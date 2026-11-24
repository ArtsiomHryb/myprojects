"""Окно входа."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from PySide6.QtCore import QPointF, QSize, QTimer, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from case_workspace.auth.service import AuthService
from case_workspace.db.models import UserAccount
from case_workspace.domain import errors


# ~7 см при 96 DPI
PASSWORD_TO_BUTTON_GAP_PX = 265


def make_eye_icon(open_eye: bool, size: int = 22) -> QIcon:
    """Иконка «глаз» в цветах темы.

    open_eye=False — закрытый глаз (пароль скрыт), нейтральный серый.
    open_eye=True  — открытый глаз (пароль виден), акцентный индиго.
    """
    color = "#4F46E5" if open_eye else "#475569"
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidthF(1.6)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)

    cx, cy = size / 2, size / 2
    w = size * 0.40
    h = size * 0.22

    if open_eye:
        path = QPainterPath()
        path.moveTo(cx - w, cy)
        path.cubicTo(cx - w * 0.5, cy - h, cx + w * 0.5, cy - h, cx + w, cy)
        path.cubicTo(cx + w * 0.5, cy + h, cx - w * 0.5, cy + h, cx - w, cy)
        p.drawPath(path)
        p.setBrush(QColor(color))
        p.drawEllipse(QPointF(cx, cy), size * 0.10, size * 0.10)
    else:
        path = QPainterPath()
        path.moveTo(cx - w, cy - 1)
        path.quadTo(cx, cy + h * 1.4, cx + w, cy - 1)
        p.drawPath(path)
        for dx in (-w * 0.55, 0, w * 0.55):
            x = cx + dx
            p.drawLine(QPointF(x, cy + h * 0.55), QPointF(x, cy + h * 1.15))

    p.end()
    return QIcon(pm)



class LoginWindow(QWidget):
    def __init__(
        self,
        auth: AuthService,
        on_success: Callable[[UserAccount], None],
        on_recover: Callable[[], None] | None = None,
        on_register: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self.auth = auth
        self.on_success = on_success
        self.on_recover = on_recover
        self.on_register = on_register
        self._locked_until: datetime | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick_lock)

        self.setWindowTitle("Case Workspace — Вход")
        self.setMinimumSize(560, 720)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(60, 32, 60, 32)
        root.setSpacing(12)

        # 1) Заголовок — по центру сверху
        title = QLabel("Вход в систему")
        title.setObjectName("h1")
        title.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        root.addWidget(title)

        root.addSpacing(24)

        # 2) Поля логин / пароль
        login_label = QLabel("Логин:")
        login_label.setObjectName("caption")
        root.addWidget(login_label)

        self.login = QLineEdit()
        self.login.setMinimumHeight(36)
        root.addWidget(self.login)

        password_label = QLabel("Пароль:")
        password_label.setObjectName("caption")
        root.addWidget(password_label)

        password_row = QHBoxLayout()
        password_row.setSpacing(4)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setMinimumHeight(36)
        self.password.returnPressed.connect(self._on_login)
        password_row.addWidget(self.password, 1)

        # 3) "Глазик" — показать/скрыть пароль
        self.toggle_pw_btn = QPushButton()
        self.toggle_pw_btn.setObjectName("togglePassword")
        self.toggle_pw_btn.setCheckable(True)
        self.toggle_pw_btn.setFixedSize(38, 38)
        self.toggle_pw_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_pw_btn.setToolTip("Показать пароль")
        self.toggle_pw_btn.setIcon(make_eye_icon(open_eye=False))
        self.toggle_pw_btn.setIconSize(QSize(20, 20))
        self.toggle_pw_btn.clicked.connect(self._toggle_password_visibility)
        password_row.addWidget(self.toggle_pw_btn, 0)
        root.addLayout(password_row)

        root.addSpacing(8)

        # 4) Ссылки: восстановить / создать учётку
        links_row = QHBoxLayout()
        self.btn_recover = QPushButton("Восстановить пароль?")
        self.btn_recover.setObjectName("linkButton")
        self.btn_recover.setCursor(Qt.PointingHandCursor)
        self.btn_recover.setFlat(True)
        self.btn_recover.clicked.connect(self._on_recover_clicked)
        links_row.addWidget(self.btn_recover, alignment=Qt.AlignLeft)

        links_row.addStretch()

        self.btn_register = QPushButton("Создать новую учётную запись?")
        self.btn_register.setObjectName("linkButton")
        self.btn_register.setCursor(Qt.PointingHandCursor)
        self.btn_register.setFlat(True)
        self.btn_register.clicked.connect(self._on_register_clicked)
        links_row.addWidget(self.btn_register, alignment=Qt.AlignRight)
        root.addLayout(links_row)

        self.status = QLabel("")
        self.status.setObjectName("danger")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignHCenter)
        root.addWidget(self.status)

        # 5) Отступ ~7 см до кнопки "Войти"
        spacer = QSpacerItem(
            0, PASSWORD_TO_BUTTON_GAP_PX, QSizePolicy.Minimum, QSizePolicy.Fixed
        )
        root.addItem(spacer)

        # 6) Кнопка "Войти" — по центру
        self.login_btn = QPushButton("Войти")
        self.login_btn.setObjectName("primary")
        self.login_btn.setMinimumHeight(42)
        self.login_btn.setMinimumWidth(200)
        self.login_btn.clicked.connect(self._on_login)
        root.addWidget(self.login_btn, alignment=Qt.AlignHCenter)

        root.addStretch()

    def _toggle_password_visibility(self) -> None:
        if self.toggle_pw_btn.isChecked():
            self.password.setEchoMode(QLineEdit.Normal)
            self.toggle_pw_btn.setIcon(make_eye_icon(open_eye=True))
            self.toggle_pw_btn.setToolTip("Скрыть пароль")
        else:
            self.password.setEchoMode(QLineEdit.Password)
            self.toggle_pw_btn.setIcon(make_eye_icon(open_eye=False))
            self.toggle_pw_btn.setToolTip("Показать пароль")

    def _on_recover_clicked(self) -> None:
        if self.on_recover:
            self.on_recover()

    def _on_register_clicked(self) -> None:
        if self.on_register:
            self.on_register()

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
        now = datetime.now(UTC)
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
