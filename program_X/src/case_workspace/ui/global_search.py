"""Глобальный поиск по делам, идентификаторам, участникам."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from case_workspace.db.models import UserAccount
from case_workspace.participants.models import Party
from case_workspace.projects.models import Case
from case_workspace.projects.service import CaseService


class GlobalSearchDialog(QDialog):
    def __init__(
        self,
        user: UserAccount,
        case_service: CaseService,
        session,
        on_open_case=None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.user = user
        self.cases = case_service
        self.session = session
        self.on_open_case = on_open_case
        self.setWindowTitle("Поиск")
        self.setMinimumSize(900, 600)
        self._results: list[tuple[int, str]] = []  # (case_id, description)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        title = QLabel("Глобальный поиск")
        title.setObjectName("h1")
        root.addWidget(title)

        row = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText(
            "Введите номер дела, ФИО, идентификатор (карта, телефон, …)"
        )
        self.query.setMinimumHeight(38)
        self.query.textChanged.connect(self._search)
        row.addWidget(self.query, 1)
        self.btn_close = QPushButton("Закрыть")
        self.btn_close.clicked.connect(self.reject)
        row.addWidget(self.btn_close)
        root.addLayout(row)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Тип", "Номер", "Описание"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(self._open_selected)
        root.addWidget(self.table, 1)

        self.hint = QLabel("Начните вводить запрос")
        self.hint.setObjectName("caption")
        root.addWidget(self.hint)

        self.query.setFocus()

    def _search(self) -> None:
        q = self.query.text().strip().lower()
        if len(q) < 2:
            self.table.setRowCount(0)
            self.hint.setText("Введите минимум 2 символа")
            return

        results: list[tuple[int, str, str, str]] = []

        from sqlalchemy import or_, select

        # 1. По номеру дела / статье
        case_q = (
            select(Case)
            .where(
                or_(
                    Case.case_number.ilike(f"%{q}%"),
                    Case.article.ilike(f"%{q}%"),
                )
            )
            .limit(20)
        )
        if self.user.role.value != "admin":
            case_q = case_q.where(Case.owner_id == self.user.id)
        for c in self.session.scalars(case_q):
            results.append(
                (
                    c.id,
                    "Дело",
                    c.case_number or "—",
                    f"{c.article or ''} · {c.accused_name or ''}".strip(" ·"),
                )
            )

        # 2. По участникам
        party_q = select(Party).where(Party.full_name.ilike(f"%{q}%")).limit(20)
        for p in self.session.scalars(party_q):
            case = self.session.get(Case, p.case_id)
            if case is None:
                continue
            if self.user.role.value != "admin" and case.owner_id != self.user.id:
                continue
            results.append(
                (
                    p.case_id,
                    "Участник",
                    p.full_name,
                    f"{p.role.label} · дело {case.case_number or '—'}",
                )
            )

        # 3. По идентификаторам
        try:
            from case_workspace.identifiers.models import Identifier

            id_q = (
                select(Identifier)
                .where(Identifier.normalized_value.ilike(f"%{q.replace(' ', '').replace('-', '')}%"))
                .limit(20)
            )
            for ident in self.session.scalars(id_q):
                case = self.session.get(Case, ident.case_id)
                if case is None:
                    continue
                if self.user.role.value != "admin" and case.owner_id != self.user.id:
                    continue
                results.append(
                    (
                        ident.case_id,
                        ident.type.label,
                        ident.value,
                        f"дело {case.case_number or '—'}",
                    )
                )
        except Exception:  # noqa: BLE001
            pass

        self.table.setRowCount(len(results))
        self._results = []
        for row, (case_id, typ, num, desc) in enumerate(results):
            self.table.setItem(row, 0, QTableWidgetItem(typ))
            self.table.setItem(row, 1, QTableWidgetItem(num))
            self.table.setItem(row, 2, QTableWidgetItem(desc))
            self._results.append((case_id, desc))
        self.hint.setText(f"Найдено: {len(results)}")

    def _open_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._results):
            return
        case_id, _ = self._results[row]
        if self.on_open_case:
            self.on_open_case(case_id)
        self.accept()
