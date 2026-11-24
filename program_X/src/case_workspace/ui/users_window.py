"""Управление пользователями (только Admin)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from case_workspace.auth.service import AuthService
from case_workspace.db.models import Role, UserAccount
from case_workspace.domain import errors


class _NewUserDialog(QDialog):
    def __init__(self, admin: UserAccount, auth: AuthService, parent=None) -> None:
        super().__init__(parent)
        self.admin = admin
        self.auth = auth
        self.created: UserAccount | None = None
        self.setWindowTitle("Новый пользователь")
        self.setMinimumWidth(480)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        title = QLabel("Создание пользователя")
        title.setObjectName("h1")
        root.addWidget(title)

        form = QFormLayout()
        self.login = QLineEdit()
        self.full_name = QLineEdit()
        self.position = QLineEdit()
        self.rank = QLineEdit()
        self.org = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        form.addRow("Логин:", self.login)
        form.addRow("ФИО:", self.full_name)
        form.addRow("Должность:", self.position)
        form.addRow("Звание:", self.rank)
        form.addRow("Место работы:", self.org)
        form.addRow("Пароль:", self.password)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Создать")
        buttons.button(QDialogButtonBox.Ok).setObjectName("primary")
        buttons.accepted.connect(self._on_create)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _on_create(self) -> None:
        try:
            user = self.auth.create_user(
                self.admin,
                login=self.login.text(),
                password=self.password.text(),
                full_name=self.full_name.text(),
                position=self.position.text(),
                rank=self.rank.text(),
                organization_name=self.org.text(),
                organ_code=self.admin.organ_code,
                territorial_code=self.admin.territorial_code,
                role=Role.USER,
            )
        except (errors.AuthError, errors.PasswordPolicyError) as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        self.created = user
        self.accept()


class UsersWindow(QWidget):
    def __init__(self, admin: UserAccount, auth: AuthService) -> None:
        super().__init__()
        self.admin = admin
        self.auth = auth
        self.setWindowTitle("Пользователи")
        self.setMinimumSize(650, 400)
        self._build()
        self._refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        title = QLabel("Пользователи")
        title.setObjectName("h1")
        root.addWidget(title)

        bar = QHBoxLayout()
        self.btn_new = QPushButton("+ Создать пользователя")
        self.btn_new.setObjectName("primary")
        self.btn_new.clicked.connect(self._new_user)
        bar.addWidget(self.btn_new)

        self.btn_toggle = QPushButton("Деактивировать / Активировать")
        self.btn_toggle.clicked.connect(self._toggle_active)
        bar.addWidget(self.btn_toggle)
        bar.addStretch()
        root.addLayout(bar)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Логин", "ФИО", "Роль", "Активен", "Telegram ID"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        root.addWidget(self.table)

    def _refresh(self) -> None:
        users = self.auth.list_users()
        self.table.setRowCount(len(users))
        for row, u in enumerate(users):
            self.table.setItem(row, 0, QTableWidgetItem(u.login))
            self.table.setItem(row, 1, QTableWidgetItem(u.full_name))
            self.table.setItem(row, 2, QTableWidgetItem(u.role.value))
            self.table.setItem(row, 3, QTableWidgetItem("да" if u.is_active else "нет"))
            self.table.setItem(
                row, 4, QTableWidgetItem(str(u.telegram_id) if u.telegram_id else "—")
            )
        self._user_ids = [u.id for u in users]
        self._user_active = [u.is_active for u in users]

    def _new_user(self) -> None:
        dlg = _NewUserDialog(self.admin, self.auth, self)
        if dlg.exec():
            self._refresh()

    def _toggle_active(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Пользователи", "Выберите пользователя.")
            return
        user_id = self._user_ids[row]
        current = self._user_active[row]
        try:
            self.auth.set_active(self.admin, user_id, not current)
        except errors.AuthError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        self._refresh()