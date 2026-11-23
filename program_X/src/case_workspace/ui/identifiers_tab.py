"""Вкладка идентификаторов в карточке дела."""

from __future__ import annotations

import json

from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from case_workspace.identifiers.models import (
    Identifier,
    IdentifierType,
    VerificationStatus,
)
from case_workspace.identifiers.service import IdentifierService
from case_workspace.participants.service import PartyService
from case_workspace.ui.identifier_dialog import IdentifierDialog

STATUS_LABEL = {
    VerificationStatus.CONFIRMED: "подтверждено",
    VerificationStatus.PARTIAL: "частично",
    VerificationStatus.CONFLICT: "расхождение",
    VerificationStatus.UNKNOWN: "неизвестно",
}


class IdentifiersTab(QWidget):
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
        self._ids: list[int] = []
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(8)

        bar = QHBoxLayout()
        self.btn_add = QPushButton("+ Добавить")
        self.btn_add.setObjectName("primary")
        self.btn_add.clicked.connect(self._add)
        bar.addWidget(self.btn_add)

        self.btn_delete = QPushButton("Удалить")
        self.btn_delete.clicked.connect(self._delete)
        bar.addWidget(self.btn_delete)

        self.btn_details = QPushButton("Детали")
        self.btn_details.clicked.connect(self._show_details)
        bar.addWidget(self.btn_details)

        bar.addStretch()
        self.summary = QLabel("")
        self.summary.setObjectName("caption")
        bar.addWidget(self.summary)
        root.addLayout(bar)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Тип", "Значение", "Определение", "Статус", "Участник"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(lambda _: self._show_details())
        root.addWidget(self.table)

    def refresh(self) -> None:
        items = self.service.list_identifiers(self.case_id)
        parties = {p.id: p for p in self.party_service.list_parties(self.case_id)}
        self.table.setRowCount(len(items))
        for row, ident in enumerate(items):
            self.table.setItem(row, 0, QTableWidgetItem(ident.type.label))
            self.table.setItem(row, 1, QTableWidgetItem(ident.value))
            self.table.setItem(row, 2, QTableWidgetItem(self._short_definition(ident)))
            self.table.setItem(
                row, 3, QTableWidgetItem(STATUS_LABEL.get(ident.verification_status, ""))
            )
            party_name = "—"
            if ident.party_id and ident.party_id in parties:
                party_name = parties[ident.party_id].full_name
            self.table.setItem(row, 4, QTableWidgetItem(party_name))
        self._ids = [i.id for i in items]
        self.summary.setText(f"Идентификаторов: {len(items)}")

    def _short_definition(self, ident: Identifier) -> str:
        for raw in (ident.resolved_local, ident.resolved_online):
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except ValueError:
                continue
            if ident.type in (IdentifierType.CARD, IdentifierType.IBAN):
                return data.get("bank_name", "") or "—"
            if ident.type == IdentifierType.PHONE:
                return data.get("carrier", "") or "—"
            if ident.type == IdentifierType.IP:
                return (
                    data.get("city", "")
                    or data.get("region", "")
                    or data.get("country", "")
                    or "—"
                )
        return "—"

    def _add(self) -> None:
        dlg = IdentifierDialog(self.case_id, self.service, self.party_service, self)
        if dlg.exec() and dlg.created:
            self.refresh()

    def _delete(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._ids):
            QMessageBox.information(self, "Удаление", "Выберите идентификатор.")
            return
        if QMessageBox.question(
            self, "Удаление", "Удалить выбранный идентификатор?"
        ) != QMessageBox.Yes:
            return
        self.service.delete(self._ids[row])
        self.refresh()

    def _show_details(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._ids):
            QMessageBox.information(self, "Детали", "Выберите идентификатор.")
            return
        items = self.service.list_identifiers(self.case_id)
        ident = next((i for i in items if i.id == self._ids[row]), None)
        if ident is None:
            return
        lines = [
            f"Тип: {ident.type.label}",
            f"Значение: {ident.value}",
            f"Нормализовано: {ident.normalized_value}",
            f"Статус: {STATUS_LABEL.get(ident.verification_status, '')}",
        ]
        if ident.verified_at:
            lines.append(f"Проверено: {ident.verified_at:%d.%m.%Y %H:%M}")
        if ident.comment:
            lines.append(f"Комментарий: {ident.comment}")
        lines += ["", "Локально:", ident.resolved_local or "  — нет"]
        lines += ["", "Онлайн:", ident.resolved_online or "  — нет"]
        QMessageBox.information(self, "Детали идентификатора", "\n".join(lines))
