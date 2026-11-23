"""Диалог добавления идентификатора."""

from __future__ import annotations

import json

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from case_workspace.identifiers.models import Identifier, IdentifierType
from case_workspace.identifiers.service import IdentifierService
from case_workspace.participants.service import PartyService


class IdentifierDialog(QDialog):
    def __init__(
        self,
        case_id: int,
        service: IdentifierService,
        party_service: PartyService,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.case_id = case_id
        self.service = service
        self.party_service = party_service
        self.created: Identifier | None = None
        self._resolved: dict | None = None

        self.setWindowTitle("Новый идентификатор")
        self.setMinimumWidth(620)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel("Добавление идентификатора")
        title.setObjectName("h1")
        root.addWidget(title)

        form = QFormLayout()

        self.value = QLineEdit()
        self.value.setPlaceholderText(
            "9112 0020 1356 1354  |  BY12 ALFA 3014 ...  |  +375 33 390-11-82  |  12.12.222.147"
        )
        self.value.textChanged.connect(self._on_value_changed)
        form.addRow("Значение:", self.value)

        self.party = QComboBox()
        self.party.addItem("— не привязан —", None)
        for p in self.party_service.list_parties(self.case_id):
            self.party.addItem(f"{p.role.label}: {p.full_name}", p.id)
        form.addRow("Участник:", self.party)

        self.comment = QLineEdit()
        form.addRow("Комментарий:", self.comment)

        root.addLayout(form)

        check_row = QHBoxLayout()
        self.btn_check = QPushButton("Проверить")
        self.btn_check.clicked.connect(self._on_check)
        check_row.addWidget(self.btn_check)
        check_row.addStretch()
        root.addLayout(check_row)

        self.result_view = QTextEdit()
        self.result_view.setReadOnly(True)
        self.result_view.setMinimumHeight(180)
        self.result_view.setPlaceholderText("Результат проверки появится здесь.")
        root.addWidget(self.result_view)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Добавить")
        buttons.button(QDialogButtonBox.Ok).setObjectName("primary")
        buttons.button(QDialogButtonBox.Cancel).setText("Отмена")
        buttons.accepted.connect(self._on_add)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _on_value_changed(self) -> None:
        self._resolved = None
        self.result_view.clear()

    def _on_check(self) -> None:
        value = self.value.text().strip()
        if not value:
            QMessageBox.information(self, "Проверка", "Введите значение.")
            return
        self.result_view.setPlainText("Проверяю… (может занять несколько секунд)")
        self.btn_check.setEnabled(False)
        try:
            self._resolved = self.service.resolve(value, use_online=True)
        except Exception as exc:  # noqa: BLE001
            self.result_view.setPlainText(f"Ошибка: {exc}")
            self.btn_check.setEnabled(True)
            return
        self.btn_check.setEnabled(True)
        if not self._resolved:
            self.result_view.setPlainText("Не удалось проверить.")
            return
        r = self._resolved
        lines = [
            f"Тип: {IdentifierType(r['type']).label}",
            f"Нормализовано: {r['normalized']}",
            f"Статус: {r['verification_status']}",
        ]
        if r.get("error"):
            lines.append(f"ВНИМАНИЕ: {r['error']}")
        lines += ["", "Локально:"]
        lines.append(
            json.dumps(r["local"], ensure_ascii=False, indent=2) if r["local"] else "  — не найдено"
        )
        lines += ["", "Онлайн:"]
        lines.append(
            json.dumps(r["online"], ensure_ascii=False, indent=2)
            if r["online"]
            else "  — не найдено"
        )
        self.result_view.setPlainText("\n".join(lines))

    def _on_add(self) -> None:
        value = self.value.text().strip()
        if not value:
            QMessageBox.warning(self, "Ошибка", "Введите значение.")
            return
        try:
            ident = self.service.add(
                self.case_id,
                value,
                party_id=self.party.currentData(),
                comment=self.comment.text().strip(),
                use_online=True,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить: {exc}")
            return
        self.created = ident
        self.accept()
