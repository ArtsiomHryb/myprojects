"""Главное окно: рабочий стол со списком дел."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from case_workspace.auth.service import AuthService
from case_workspace.db.models import Role, UserAccount
from case_workspace.participants.service import PartyService
from case_workspace.projects.service import CaseService
from case_workspace.ui.case_dialog import CaseDialog
from case_workspace.ui.case_window import CaseWindow
from case_workspace.ui.users_window import UsersWindow


class MainWindow(QMainWindow):
    def __init__(
        self,
        user: UserAccount,
        auth_service: AuthService,
        case_service: CaseService,
        party_service: PartyService,
        on_logout: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self.user = user
        self.auth_service = auth_service
        self.case_service = case_service
        self.party_service = party_service
        self.on_logout = on_logout
        self.case_windows: list[CaseWindow] = []
        self.users_window: UsersWindow | None = None

        self.setWindowTitle("Case Workspace")
        self.setMinimumSize(1100, 720)
        self._build_ui()
        self._refresh_cases()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        # --- Шапка ---
        header = QHBoxLayout()
        title = QLabel(f"Добро пожаловать, {self.user.full_name or self.user.login}")
        title.setObjectName("h1")
        header.addWidget(title)

        role_label = QLabel(f"  ({self.user.role.value})")
        role_label.setObjectName("caption")
        header.addWidget(role_label)
        header.addStretch()

        if self.user.role == Role.ADMIN:
            self.btn_users = QPushButton("Пользователи")
            self.btn_users.clicked.connect(self._open_users)
            header.addWidget(self.btn_users)

        self.btn_logout = QPushButton("Выйти")
        self.btn_logout.clicked.connect(self._logout)
        header.addWidget(self.btn_logout)

        root.addLayout(header)

        # --- Панель действий ---
        bar = QHBoxLayout()
        self.btn_new_case = QPushButton("+ Новое дело")
        self.btn_new_case.setObjectName("primary")
        self.btn_new_case.clicked.connect(self._new_case)
        bar.addWidget(self.btn_new_case)

        self.btn_open_case = QPushButton("Открыть дело")
        self.btn_open_case.clicked.connect(self._open_selected_case)
        bar.addWidget(self.btn_open_case)

        self.btn_refresh = QPushButton("Обновить")
        self.btn_refresh.clicked.connect(self._refresh_cases)
        bar.addWidget(self.btn_refresh)

        bar.addStretch()
        self.summary = QLabel("")
        self.summary.setObjectName("caption")
        bar.addWidget(self.summary)
        root.addLayout(bar)

        # --- Таблица дел ---
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Номер", "Статья", "Возбуждено", "Срок до", "Дней", "Орган", "Статус"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self._open_selected_case)
        root.addWidget(self.table)

        self.setCentralWidget(central)

    # --- действия ---

    def _refresh_cases(self) -> None:
        cases = self.case_service.list_cases(self.user)
        self.table.setRowCount(len(cases))
        for row, c in enumerate(cases):
            days = self.case_service.days_left(c)
            self.table.setItem(row, 0, QTableWidgetItem(c.case_number or "—"))
            self.table.setItem(row, 1, QTableWidgetItem(c.article))
            self.table.setItem(row, 2, QTableWidgetItem(c.initiated_at.strftime("%d.%m.%Y")))
            self.table.setItem(row, 3, QTableWidgetItem(c.current_deadline.strftime("%d.%m.%Y")))
            days_item = QTableWidgetItem(str(days))
            if days < 0:
                days_item.setForeground(Qt.red)
            elif days <= 14:
                days_item.setForeground(Qt.darkYellow)
            self.table.setItem(row, 4, days_item)
            self.table.setItem(row, 5, QTableWidgetItem(c.originating_agency))
            self.table.setItem(row, 6, QTableWidgetItem(c.location_status.value))
        self._case_ids = [c.id for c in cases]
        self.summary.setText(f"Всего дел: {len(cases)}")

    def _new_case(self) -> None:
        dlg = CaseDialog(self.user, self.case_service, self)
        if dlg.exec() and dlg.created_case_id:
            self._refresh_cases()
            case = self.case_service.get_case(dlg.created_case_id)
            if case is not None:
                self._open_case_window(case)

    def _open_selected_case(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(getattr(self, "_case_ids", [])):
            QMessageBox.information(self, "Дела", "Выберите дело.")
            return
        case = self.case_service.get_case(self._case_ids[row])
        if case is not None:
            self._open_case_window(case)

    def _open_case_window(self, case) -> None:
        window = CaseWindow(
            case,
            self.user,
            self.case_service,
            self.party_service,
            on_close=self._refresh_cases,
        )
        self.case_windows.append(window)
        window.show()

    def _open_users(self) -> None:
        if self.users_window is None:
            self.users_window = UsersWindow(self.user, self.auth_service)
        self.users_window.show()
        self.users_window.raise_()

    def _logout(self) -> None:
        if (
            QMessageBox.question(self, "Выход", "Выйти из программы?")
            != QMessageBox.Yes
        ):
            return
        for w in self.case_windows:
            w.close()
        if self.users_window:
            self.users_window.close()
        if self.on_logout:
            self.on_logout()
        self.close()