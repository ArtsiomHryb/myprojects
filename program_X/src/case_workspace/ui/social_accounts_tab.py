"""Вкладка учётных записей (соцсети и мессенджеры)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from case_workspace.crypto.models import SocialPlatform
from case_workspace.crypto.services import SocialService
from case_workspace.participants.service import PartyService


class _AccountDialog(QDialog):
    def __init__(self, case_id, social_service, party_service, parent=None):
        super().__init__(parent)
        self.case_id = case_id
        self.social = social_service
        self.party_service = party_service
        self.created = None
        self.setWindowTitle("Новая учётная запись")
        self.setMinimumWidth(600)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        title = QLabel("Добавление учётной записи")
        title.setObjectName("h1")
        root.addWidget(title)

        form = QFormLayout()

        self.platform = QComboBox()
        for p in SocialPlatform:
            self.platform.addItem(p.label, p)
        self.platform.currentIndexChanged.connect(self._on_platform)
        form.addRow("Платформа:", self.platform)

        self.platform_other = QLineEdit()
        self.platform_other.setEnabled(False)
        self.platform_other.setPlaceholderText("Название платформы")
        form.addRow("Другое:", self.platform_other)

        self.username = QLineEdit()
        self.username.setPlaceholderText("@username")
        form.addRow("Username:", self.username)

        self.user_id = QLineEdit()
        form.addRow("ID платформы:", self.user_id)

        self.profile_url = QLineEdit()
        self.profile_url.setPlaceholderText("https://...")
        form.addRow("Ссылка:", self.profile_url)

        self.display_name = QLineEdit()
        form.addRow("Отображаемое имя:", self.display_name)

        self.phone = QLineEdit()
        self.phone.setPlaceholderText("+375...")
        form.addRow("Телефон:", self.phone)

        self.email = QLineEdit()
        form.addRow("Email:", self.email)

        self.party = QComboBox()
        self.party.addItem("— не привязан —", None)
        for p in self.party_service.list_parties(self.case_id):
            self.party.addItem(f"{p.role.label}: {p.full_name}", p.id)
        form.addRow("Участник:", self.party)

        self.label = QLineEdit()
        form.addRow("Метка:", self.label)

        self.bio = QTextEdit()
        self.bio.setMaximumHeight(60)
        form.addRow("Bio:", self.bio)

        self.notes = QTextEdit()
        self.notes.setMaximumHeight(60)
        form.addRow("Заметки:", self.notes)

        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Добавить")
        buttons.button(QDialogButtonBox.Ok).setObjectName("primary")
        buttons.accepted.connect(self._on_add)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _on_platform(self):
        is_other = self.platform.currentData() == SocialPlatform.OTHER
        self.platform_other.setEnabled(is_other)

    def _on_add(self):
        try:
            acc = self.social.add_account(
                self.case_id,
                platform=self.platform.currentData(),
                party_id=self.party.currentData(),
                username=self.username.text(),
                user_id=self.user_id.text(),
                profile_url=self.profile_url.text(),
                display_name=self.display_name.text(),
                phone=self.phone.text(),
                email=self.email.text(),
                bio=self.bio.toPlainText(),
                label=self.label.text(),
                notes=self.notes.toPlainText(),
                platform_other=self.platform_other.text(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        self.created = acc
        self.accept()


class SocialAccountsTab(QWidget):
    def __init__(self, case_id, social_service, party_service, parent=None):
        super().__init__(parent)
        self.case_id = case_id
        self.social = social_service
        self.party_service = party_service
        self._ids = []
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(8)

        bar = QHBoxLayout()
        self.btn_add = QPushButton("+ Добавить учётную запись")
        self.btn_add.setObjectName("primary")
        self.btn_add.clicked.connect(self._add)
        bar.addWidget(self.btn_add)

        self.btn_delete = QPushButton("Удалить")
        self.btn_delete.clicked.connect(self._delete)
        bar.addWidget(self.btn_delete)

        bar.addStretch()
        self.summary = QLabel("")
        self.summary.setObjectName("caption")
        bar.addWidget(self.summary)
        root.addLayout(bar)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Платформа", "Username", "ID", "Телефон", "Участник", "Метка"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        root.addWidget(self.table)

    def refresh(self):
        accounts = self.social.list_accounts(self.case_id)
        parties = {p.id: p for p in self.party_service.list_parties(self.case_id)}
        self.table.setRowCount(len(accounts))
        for row, a in enumerate(accounts):
            self.table.setItem(row, 0, QTableWidgetItem(a.platform_enum.label))
            self.table.setItem(row, 1, QTableWidgetItem(a.username or "—"))
            self.table.setItem(row, 2, QTableWidgetItem(a.user_id or "—"))
            self.table.setItem(row, 3, QTableWidgetItem(a.phone or "—"))
            party = parties.get(a.party_id)
            self.table.setItem(
                row, 4, QTableWidgetItem(party.full_name if party else "—")
            )
            self.table.setItem(row, 5, QTableWidgetItem(a.label or "—"))
        self._ids = [a.id for a in accounts]
        self.summary.setText(f"Учётных записей: {len(accounts)}")

    def _add(self):
        dlg = _AccountDialog(self.case_id, self.social, self.party_service, self)
        if dlg.exec() and dlg.created:
            self.refresh()

    def _delete(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._ids):
            QMessageBox.information(self, "Удаление", "Выберите учётную запись.")
            return
        if QMessageBox.question(
            self, "Удаление", "Удалить выбранную учётную запись?"
        ) != QMessageBox.Yes:
            return
        self.social.delete_account(self._ids[row])
        self.refresh()
