"""Окно дела с вкладками."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from case_workspace.db.models import UserAccount
from case_workspace.participants.service import PartyService
from case_workspace.projects.models import Case
from case_workspace.projects.service import CaseService
from case_workspace.ui.party_dialog import PartyDialog
from case_workspace.identifiers.service import IdentifierService
from case_workspace.ui.identifiers_tab import IdentifiersTab
from case_workspace.ui.crypto_wallets_tab import CryptoWalletsTab
from case_workspace.ui.social_accounts_tab import SocialAccountsTab
from case_workspace.crypto.services import CryptoService, SocialService
from case_workspace.documents.services import DocumentService
from case_workspace.templates.service import TemplateService
from case_workspace.ui.documents_tab import DocumentsTab
from case_workspace.legal.service import LegalService
from case_workspace.ui.article_window import ArticleWindow
from case_workspace.ui.time_tracking_tab import TimeTrackingTab
from case_workspace.timetracking.service import TimeService


class CaseWindow(QWidget):
    def __init__(
        self,
        case: Case,
        user: UserAccount,
        case_service: CaseService,
        party_service: PartyService,
        identifier_service: IdentifierService,
        crypto_service: CryptoService,
        social_service: SocialService,
        document_service: DocumentService,
        template_service: TemplateService,
        time_service: TimeService,
        on_close=None,
    ) -> None:
        super().__init__()
        self.case = case
        self.user = user
        self.case_service = case_service
        self.party_service = party_service
        self.identifier_service = identifier_service
        self.crypto_service = crypto_service
        self.social_service = social_service
        self.document_service = document_service
        self.template_service = template_service
        self.time_service = time_service
        self.on_close = on_close

        self.setWindowTitle(f"Дело {case.case_number or '— эпизод —'}")
        self.setMinimumSize(800, 550)
        self._build_ui()
        self._refresh_parties()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # Шапка
        header = QHBoxLayout()
        title = QLabel(f"Дело {self.case.case_number or '— эпизод —'}")
        title.setObjectName("h1")
        header.addWidget(title)
        header.addStretch()
        self.btn_extend = QPushButton("Продлить срок")
        self.btn_extend.clicked.connect(self._extend_deadline)
        header.addWidget(self.btn_extend)
        self.btn_archive = QPushButton("В архив")
        self.btn_archive.clicked.connect(self._archive)
        header.addWidget(self.btn_archive)
        root.addLayout(header)

        # Вкладки
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        self.tabs.addTab(self._build_overview_tab(), "Обзор")
        self.tabs.addTab(self._build_parties_tab(), "Участники")

        self.time_tab = TimeTrackingTab(self.case.id, self.time_service, self)
        self.tabs.addTab(self.time_tab, "Тайминг")

        self.documents_tab = DocumentsTab(
            self.case.id,
            self.document_service,
            self.template_service,
            self.party_service,
            self,
        )
        self.tabs.addTab(self.documents_tab, "Документы")
        self.identifiers_tab = IdentifiersTab(
            self.case.id, self.identifier_service, self.party_service, self
        )
        self.tabs.addTab(self.identifiers_tab, "Идентификаторы")

        self.wallets_tab = CryptoWalletsTab(
            self.case.id, self.crypto_service, self.party_service, self
        )
        self.tabs.addTab(self.wallets_tab, "Криптокошельки")

        self.socials_tab = SocialAccountsTab(
            self.case.id, self.social_service, self.party_service, self
        )
        self.tabs.addTab(self.socials_tab, "Учётные записи")

        # Кнопка "Закрыть"
        bottom = QHBoxLayout()
        bottom.addStretch()
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self._on_close)
        bottom.addWidget(btn_close)
        root.addLayout(bottom)

    def _build_overview_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        lines = [
            ("Номер дела:", self.case.case_number or "—"),
            ("Статья:", self.case.article or "—"),
            ("Возбуждено:", self.case.initiated_at.strftime("%d.%m.%Y")),
            ("Срок до:", self.case.current_deadline.strftime("%d.%m.%Y")),
            ("Дней осталось:", str(self.case_service.days_left(self.case))),
            ("Орган:", self.case.originating_agency or "—"),
            ("Статус:", self.case.location_status.value),
            ("Цвет-тег:", self.case.color_tag or "—"),
        ]
        for label, value in lines:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setMinimumWidth(140)
            lbl.setObjectName("caption")
            val = QLabel(str(value))
            row.addWidget(lbl)
            row.addWidget(val)
            row.addStretch()
            if label == "Статья:" and self.case.article_code:
                btn_article = QPushButton("📖 Статья")
                btn_article.clicked.connect(self._open_article)
                row.addWidget(btn_article)
                btn_comment = QPushButton("💬 Комментарии")
                btn_comment.clicked.connect(self._open_comments)
                row.addWidget(btn_comment)
            layout.addLayout(row)

        layout.addStretch()
        return w

    def _open_article(self) -> None:
        legal = LegalService(self.case_service.session)
        window = ArticleWindow(
            self.case.article_code, self.case.article_part, legal, self
        )
        window.exec()

    def _open_comments(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        legal = LegalService(self.case_service.session)
        url = legal.build_comment_search_url(self.case.article_code, self.case.article_part)
        QDesktopServices.openUrl(QUrl(url))

    def _build_parties_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        bar = QHBoxLayout()
        self.btn_add_party = QPushButton("+ Добавить участника")
        self.btn_add_party.setObjectName("primary")
        self.btn_add_party.clicked.connect(self._add_party)
        bar.addWidget(self.btn_add_party)
        self.btn_del_party = QPushButton("Удалить")
        self.btn_del_party.clicked.connect(self._delete_party)
        bar.addWidget(self.btn_del_party)
        bar.addStretch()
        layout.addLayout(bar)

        self.parties_table = QTableWidget(0, 5)
        self.parties_table.setHorizontalHeaderLabels(
            ["Роль", "ФИО", "Дата рожд.", "Паспорт", "Телефон"]
        )
        self.parties_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.parties_table.horizontalHeader().setStretchLastSection(True)
        self.parties_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.parties_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.parties_table)
        return w

    def _placeholder(self, text: str) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        lbl = QLabel(text)
        lbl.setObjectName("hint")
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)
        return w

    # --- действия ---

    def _refresh_parties(self) -> None:
        parties = self.party_service.list_parties(self.case.id)
        self.parties_table.setRowCount(len(parties))
        for row, p in enumerate(parties):
            self.parties_table.setItem(row, 0, QTableWidgetItem(p.role.label))
            self.parties_table.setItem(row, 1, QTableWidgetItem(p.full_name))
            self.parties_table.setItem(
                row, 2, QTableWidgetItem(p.birth_date.strftime("%d.%m.%Y") if p.birth_date else "")
            )
            self.parties_table.setItem(row, 3, QTableWidgetItem(p.passport_id))
            self.parties_table.setItem(row, 4, QTableWidgetItem(p.contact_phone))
        self._party_ids = [p.id for p in parties]

    def _add_party(self) -> None:
        dlg = PartyDialog(self.case.id, self.party_service, self)
        if dlg.exec():
            self._refresh_parties()

    def _delete_party(self) -> None:
        row = self.parties_table.currentRow()
        if row < 0 or row >= len(getattr(self, "_party_ids", [])):
            QMessageBox.information(self, "Удаление", "Выберите участника.")
            return
        if (
            QMessageBox.question(
                self, "Удаление", "Удалить выбранного участника?"
            )
            != QMessageBox.Yes
        ):
            return
        self.party_service.delete_party(self._party_ids[row])
        self._refresh_parties()

    def _extend_deadline(self) -> None:
        # Простой диалог ввода новой даты
        from PySide6.QtWidgets import QInputDialog

        current = self.case.current_deadline.strftime("%d.%m.%Y")
        text, ok = QInputDialog.getText(
            self, "Продление срока", f"Текущий срок: {current}\nНовая дата (ДД.ММ.ГГГГ):"
        )
        if not ok or not text.strip():
            return
        try:
            d, m, y = text.strip().split(".")
            new_date = date(int(y), int(m), int(d))
        except (ValueError, AttributeError):
            QMessageBox.warning(self, "Ошибка", "Формат ДД.ММ.ГГГГ.")
            return
        reason, _ = QInputDialog.getText(self, "Продление срока", "Основание продления:")
        try:
            self.case_service.extend_deadline(self.case.id, new_date, reason or "")
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        self.case = self.case_service.get_case(self.case.id)
        self._rebuild()

    def _archive(self) -> None:
        if (
            QMessageBox.question(self, "Архив", "Переместить дело в архив?")
            != QMessageBox.Yes
        ):
            return
        self.case_service.archive(self.case.id)
        self._on_close()

    def _rebuild(self) -> None:
        # Простое пересоздание вкладок
        while self.tabs.count():
            self.tabs.removeTab(0)
        self.tabs.addTab(self._build_overview_tab(), "Обзор")
        self.tabs.addTab(self._build_parties_tab(), "Участники")

        self.time_tab = TimeTrackingTab(self.case.id, self.time_service, self)
        self.tabs.addTab(self.time_tab, "Тайминг")

        self.documents_tab = DocumentsTab(
            self.case.id,
            self.document_service,
            self.template_service,
            self.party_service,
            self,
        )
        self.tabs.addTab(self.documents_tab, "Документы")
        self.identifiers_tab = IdentifiersTab(
            self.case.id, self.identifier_service, self.party_service, self
        )
        self.tabs.addTab(self.identifiers_tab, "Идентификаторы")

        self.wallets_tab = CryptoWalletsTab(
            self.case.id, self.crypto_service, self.party_service, self
        )
        self.tabs.addTab(self.wallets_tab, "Криптокошельки")

        self.socials_tab = SocialAccountsTab(
            self.case.id, self.social_service, self.party_service, self
        )
        self.tabs.addTab(self.socials_tab, "Учётные записи")
        self._refresh_parties()

    def _on_close(self) -> None:
        if self.on_close:
            self.on_close()
        self.close()