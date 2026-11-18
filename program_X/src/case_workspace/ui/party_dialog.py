"""Диалог добавления участника."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from case_workspace.participants.models import PartyRole
from case_workspace.participants.service import PartyService


class PartyDialog(QDialog):
    def __init__(self, case_id: int, service: PartyService, parent=None) -> None:
        super().__init__(parent)
        self.case_id = case_id
        self.service = service
        self.added_party_id: int | None = None

        self.setWindowTitle("Новый участник")
        self.setMinimumWidth(520)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel("Добавление участника")
        title.setObjectName("h1")
        root.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self.role = QComboBox()
        for r in PartyRole:
            self.role.addItem(r.label, r)
        form.addRow("Роль:", self.role)

        self.full_name = QLineEdit()
        self.full_name.setPlaceholderText("Иванов Иван Иванович")
        form.addRow("ФИО:", self.full_name)

        self.birth_date = QLineEdit()
        self.birth_date.setPlaceholderText("ДД.ММ.ГГГГ (опционально)")
        form.addRow("Дата рожд.:", self.birth_date)

        self.registration = QLineEdit()
        form.addRow("Регистрация:", self.registration)

        self.residence = QLineEdit()
        form.addRow("Жительство:", self.residence)

        self.passport = QLineEdit()
        self.passport.setPlaceholderText("MP1234567")
        form.addRow("Паспорт:", self.passport)

        self.phone = QLineEdit()
        self.phone.setPlaceholderText("+375291234567")
        form.addRow("Телефон:", self.phone)

        self.comment = QLineEdit()
        form.addRow("Комментарий:", self.comment)

        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Добавить")
        buttons.button(QDialogButtonBox.Ok).setObjectName("primary")
        buttons.button(QDialogButtonBox.Cancel).setText("Отмена")
        buttons.accepted.connect(self._on_add)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _parse_date(self, text: str) -> date | None:
        text = text.strip()
        if not text:
            return None
        try:
            d, m, y = text.split(".")
            return date(int(y), int(m), int(d))
        except (ValueError, AttributeError):
            raise ValueError("Дата должна быть в формате ДД.ММ.ГГГГ.") from None

    def _on_add(self) -> None:
        try:
            birth = self._parse_date(self.birth_date.text())
            party = self.service.add_party(
                self.case_id,
                role=self.role.currentData(),
                full_name=self.full_name.text(),
                birth_date=birth,
                registration_address=self.registration.text(),
                residence_address=self.residence.text(),
                passport_id=self.passport.text(),
                contact_phone=self.phone.text(),
                comment=self.comment.text(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        self.added_party_id = party.id
        self.accept()