"""Окно регистрации первого администратора."""

from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from case_workspace.auth.service import AuthService
from case_workspace.db.models import UserAccount
from case_workspace.domain import errors


class RegisterWindow(QWidget):
    def __init__(self, auth: AuthService, on_success: Callable[[UserAccount], None]) -> None:
        super().__init__()
        self.auth = auth
        self.on_success = on_success
        self.setWindowTitle("Case Workspace — Регистрация администратора")
        self.setMinimumSize(560, 680)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 24, 32, 24)
        root.setSpacing(12)

        title = QLabel("Регистрация администратора")
        title.setObjectName("h1")
        root.addWidget(title)

        subtitle = QLabel(
            "Это первый запуск программы. Заполните данные — они будут "
            "подставляться в документы."
        )
        subtitle.setObjectName("caption")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        # Личные данные
        personal = QGroupBox("Личные данные")
        pf = QFormLayout(personal)
        self.full_name = QLineEdit()
        self.position = QLineEdit()
        self.rank = QLineEdit()
        self.organization_name = QLineEdit()
        pf.addRow("ФИО:", self.full_name)
        pf.addRow("Должность:", self.position)
        pf.addRow("Звание:", self.rank)
        pf.addRow("Место работы:", self.organization_name)
        root.addWidget(personal)

        # Реквизиты
        req = QGroupBox("Реквизиты для номера дел")
        rf = QFormLayout(req)
        self.organ_code = QLineEdit()
        self.organ_code.setMaxLength(2)
        self.organ_code.setPlaceholderText("2 цифры, напр. 12")
        self.territorial_code = QLineEdit()
        self.territorial_code.setMaxLength(3)
        self.territorial_code.setPlaceholderText("3 цифры, напр. 104")
        rf.addRow("Код органа:", self.organ_code)
        rf.addRow("Территориальный код:", self.territorial_code)
        root.addWidget(req)

        # Учётная запись
        auth_box = QGroupBox("Учётная запись")
        af = QFormLayout(auth_box)
        self.login = QLineEdit()
        self.login.setPlaceholderText("например, admin")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("8–10 символов")
        self.password2 = QLineEdit()
        self.password2.setEchoMode(QLineEdit.Password)
        af.addRow("Логин:", self.login)
        af.addRow("Пароль:", self.password)
        af.addRow("Повтор пароля:", self.password2)
        hint = QLabel(
            "Требования к паролю: 8–10 символов, минимум 2 заглавные, "
            "2 строчные, 1 цифра, 1 специальный символ."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        af.addRow(hint)
        root.addWidget(auth_box)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.register_btn = QPushButton("Зарегистрироваться")
        self.register_btn.setObjectName("primary")
        self.register_btn.clicked.connect(self._on_register)
        btn_row.addWidget(self.register_btn)
        root.addLayout(btn_row)

    def _on_register(self) -> None:
        if self.password.text() != self.password2.text():
            QMessageBox.warning(self, "Ошибка", "Пароли не совпадают.")
            return

        try:
            user = self.auth.register_first_admin(
                login=self.login.text(),
                password=self.password.text(),
                full_name=self.full_name.text(),
                position=self.position.text(),
                rank=self.rank.text(),
                organization_name=self.organization_name.text(),
                organ_code=self.organ_code.text(),
                territorial_code=self.territorial_code.text(),
            )
        except errors.PasswordPolicyError as exc:
            QMessageBox.warning(self, "Политика пароля", str(exc))
            return
        except errors.AuthError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {exc}")
            return

        QMessageBox.information(
            self, "Готово", f"Администратор {user.full_name or user.login} зарегистрирован."
        )
        self.on_success(user)