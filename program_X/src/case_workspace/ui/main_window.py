"""Главное окно: рабочий стол (иконки / список)."""

from __future__ import annotations

from datetime import date
from typing import Callable

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from case_workspace.auth.service import AuthService
from case_workspace.crypto.services import CryptoService, SocialService
from case_workspace.db.models import Role, UserAccount
from case_workspace.documents.services import DocumentService
from case_workspace.identifiers.service import IdentifierService
from case_workspace.participants.service import PartyService
from case_workspace.projects.service import CaseService
from case_workspace.templates.service import TemplateService
from case_workspace.timetracking.service import TimeService
from case_workspace.ui.backup_window import BackupWindow
from case_workspace.ui.timeline_window import TimelineWindow
from case_workspace.ui.stats_window import StatsWindow
from case_workspace.ui.case_dialog import CaseDialog
from case_workspace.ui.case_window import CaseWindow
from case_workspace.ui.desktop_view import DesktopView
from case_workspace.ui.inbox_window import InboxWindow
from case_workspace.ui.storage_locations_window import StorageLocationsWindow
from case_workspace.ui.templates_catalog_window import TemplatesCatalogWindow
from case_workspace.ui.users_window import UsersWindow


class MainWindow(QMainWindow):
    def __init__(
        self,
        user: UserAccount,
        auth_service: AuthService,
        case_service: CaseService,
        party_service: PartyService,
        identifier_service: IdentifierService,
        crypto_service: CryptoService,
        social_service: SocialService,
        document_service: DocumentService,
        template_service: TemplateService,
        time_service: TimeService,
        session,
        on_logout: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self.user = user
        self.auth_service = auth_service
        self.case_service = case_service
        self.party_service = party_service
        self.identifier_service = identifier_service
        self.crypto_service = crypto_service
        self.social_service = social_service
        self.document_service = document_service
        self.template_service = template_service
        self.time_service = time_service
        self.session = session
        self.on_logout = on_logout

        self.case_windows: list[CaseWindow] = []
        self.users_window: UsersWindow | None = None
        self.templates_window: TemplatesCatalogWindow | None = None
        self.storage_window: StorageLocationsWindow | None = None
        self.inbox_window: InboxWindow | None = None
        self.backup_window: BackupWindow | None = None

        self._view_mode = "icons"  # или "list"
        self._suppress_order_signal = False

        self.setWindowTitle("Case Workspace")
        self.setMinimumSize(1000, 650)
        self._build_ui()
        self._refresh_cases()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        # Шапка
        header = QHBoxLayout()
        title = QLabel(f"Добро пожаловать, {self.user.full_name or self.user.login}")
        title.setObjectName("h1")
        header.addWidget(title)

        role_label = QLabel(f"  ({self.user.role.value})")
        role_label.setObjectName("caption")
        header.addWidget(role_label)
        header.addStretch()

        if self.user.role == Role.ADMIN:
            self.btn_templates = QPushButton("Каталог бланков")
            self.btn_templates.clicked.connect(self._open_templates)
            header.addWidget(self.btn_templates)

            self.btn_storage = QPushButton("Локации")
            self.btn_storage.clicked.connect(self._open_storage)
            header.addWidget(self.btn_storage)

            self.btn_backup = QPushButton("Бэкап")
            self.btn_backup.clicked.connect(self._open_backup)
            header.addWidget(self.btn_backup)

            self.btn_timeline = QPushButton("Тайминг")
            self.btn_timeline.clicked.connect(self._open_timeline)
            header.addWidget(self.btn_timeline)

            self.btn_stats = QPushButton("Статистика")
            self.btn_stats.clicked.connect(self._open_stats)
            header.addWidget(self.btn_stats)

            self.btn_inbox = QPushButton("Неразобранное")
            self.btn_inbox.clicked.connect(self._open_inbox)
            header.addWidget(self.btn_inbox)

            self.btn_users = QPushButton("Пользователи")
            self.btn_users.clicked.connect(self._open_users)
            header.addWidget(self.btn_users)

            self.btn_bot = QPushButton("Бот")
            self.btn_bot.clicked.connect(self._open_bot)
            header.addWidget(self.btn_bot)

        self.btn_theme = QPushButton("🌙")
        self.btn_theme.setMaximumWidth(40)
        self.btn_theme.setToolTip("Переключить тему (светлая/тёмная)")
        self.btn_theme.clicked.connect(self._toggle_theme)
        header.addWidget(self.btn_theme)

        self.btn_logout = QPushButton("Выйти")
        self.btn_logout.clicked.connect(self._logout)
        header.addWidget(self.btn_logout)
        root.addLayout(header)

        # Панель действий
        bar = QHBoxLayout()
        self.btn_new_case = QPushButton("+ Новое дело")
        self.btn_new_case.setObjectName("primary")
        self.btn_new_case.clicked.connect(self._new_case)
        bar.addWidget(self.btn_new_case)

        self.btn_open_case = QPushButton("Открыть")
        self.btn_open_case.clicked.connect(self._open_selected_case)
        bar.addWidget(self.btn_open_case)

        if self.user.role != Role.ADMIN:
            self.btn_timeline_user = QPushButton("Тайминг")
            self.btn_timeline_user.clicked.connect(self._open_timeline)
            bar.addWidget(self.btn_timeline_user)

            self.btn_stats_user = QPushButton("Статистика")
            self.btn_stats_user.clicked.connect(self._open_stats)
            bar.addWidget(self.btn_stats_user)

        self.btn_view_toggle = QPushButton("Список")
        self.btn_view_toggle.clicked.connect(self._toggle_view)
        bar.addWidget(self.btn_view_toggle)

        self.btn_reset_order = QPushButton("Сбросить порядок")
        self.btn_reset_order.clicked.connect(self._reset_order)
        bar.addWidget(self.btn_reset_order)

        self.btn_refresh = QPushButton("Обновить")
        self.btn_refresh.clicked.connect(self._refresh_cases)
        bar.addWidget(self.btn_refresh)

        bar.addStretch()
        self.summary = QLabel("")
        self.summary.setObjectName("caption")
        bar.addWidget(self.summary)
        root.addLayout(bar)

        # Стек: иконки / список
        self.stack = QStackedWidget()

        self.icon_view = DesktopView()
        self.icon_view.case_activated.connect(self._open_case_by_id)
        self.icon_view._model.rowsMoved.connect(self._on_rows_moved)
        self.stack.addWidget(self.icon_view)

        self.list_view = QTableWidget(0, 7)
        self.list_view.setHorizontalHeaderLabels(
            ["Номер", "Статья", "Возбуждено", "Срок до", "Дней", "Обвиняемый", "Статус"]
        )
        self.list_view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.list_view.horizontalHeader().setStretchLastSection(True)
        self.list_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.list_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.list_view.doubleClicked.connect(self._open_selected_case)
        self.stack.addWidget(self.list_view)

        root.addWidget(self.stack, 1)
        self.setCentralWidget(central)

    # --- загрузка данных ---
    def _refresh_cases(self) -> None:
        cases = self.case_service.list_cases(self.user)
        order_map = self.case_service.get_desktop_order_map()

        def sort_key(c):
            idx = order_map.get(c.id)
            return (0, idx) if idx is not None else (1, c.id)

        sorted_cases = sorted(cases, key=sort_key)

        # 1. Иконки
        items_for_icons: list[tuple] = []
        for c in sorted_cases:
            days = self.case_service.days_left(c)
            items_for_icons.append((c, days))
        self._suppress_order_signal = True
        self.icon_view.populate(items_for_icons)
        self._suppress_order_signal = False

        # 2. Список
        self.list_view.setRowCount(len(sorted_cases))
        for row, c in enumerate(sorted_cases):
            days = self.case_service.days_left(c)
            self.list_view.setItem(row, 0, QTableWidgetItem(c.case_number or "—"))
            self.list_view.setItem(row, 1, QTableWidgetItem(c.article))
            self.list_view.setItem(
                row, 2, QTableWidgetItem(c.initiated_at.strftime("%d.%m.%Y"))
            )
            self.list_view.setItem(
                row, 3, QTableWidgetItem(c.current_deadline.strftime("%d.%m.%Y"))
            )
            days_item = QTableWidgetItem(str(days))
            if days < 0:
                days_item.setForeground(Qt.red)
            elif days <= 14:
                days_item.setForeground(Qt.darkYellow)
            self.list_view.setItem(row, 4, days_item)
            self.list_view.setItem(row, 5, QTableWidgetItem(c.accused_name or "—"))
            self.list_view.setItem(row, 6, QTableWidgetItem(c.location_status.value))
        self._list_case_ids = [c.id for c in sorted_cases]

        self.summary.setText(f"Всего дел: {len(sorted_cases)}")

    # --- переключение вида ---
    def _toggle_view(self) -> None:
        if self._view_mode == "icons":
            self._view_mode = "list"
            self.stack.setCurrentWidget(self.list_view)
            self.btn_view_toggle.setText("Иконки")
        else:
            self._view_mode = "icons"
            self.stack.setCurrentWidget(self.icon_view)
            self.btn_view_toggle.setText("Список")

    # --- перетаскивание: сохранение порядка ---
    def _on_rows_moved(self, *args) -> None:
        if self._suppress_order_signal:
            return
        pairs: list[tuple[int, int]] = []
        for i in range(self.icon_view.count()):
            item = self.icon_view.item(i)
            case_id = item.data(Qt.UserRole)
            if case_id is not None:
                pairs.append((int(case_id), i))
        if pairs:
            try:
                self.case_service.set_desktop_orders_bulk(pairs)
            except Exception:  # noqa: BLE001
                pass

    def _reset_order(self) -> None:
        if QMessageBox.question(
            self, "Сброс порядка", "Сбросить порядок иконок?"
        ) != QMessageBox.Yes:
            return
        self.case_service.reset_desktop_order()
        self._refresh_cases()

    # --- действия ---
    def _new_case(self) -> None:
        dlg = CaseDialog(self.user, self.case_service, self)
        if dlg.exec() and dlg.created_case_id:
            self._refresh_cases()
            case = self.case_service.get_case(dlg.created_case_id)
            if case is not None:
                self._open_case_window(case)

    def _selected_case_id(self) -> int | None:
        if self._view_mode == "icons":
            return self.icon_view.selected_case_id()
        row = self.list_view.currentRow()
        if 0 <= row < len(getattr(self, "_list_case_ids", [])):
            return self._list_case_ids[row]
        return None

    def _open_selected_case(self) -> None:
        cid = self._selected_case_id()
        if cid is None:
            QMessageBox.information(self, "Открыть", "Выберите дело.")
            return
        self._open_case_by_id(cid)

    def _open_case_by_id(self, case_id: int) -> None:
        case = self.case_service.get_case(case_id)
        if case is not None:
            self._open_case_window(case)

    def _open_case_window(self, case) -> None:
        window = CaseWindow(
            case,
            self.user,
            self.case_service,
            self.party_service,
            self.identifier_service,
            self.crypto_service,
            self.social_service,
            self.document_service,
            self.template_service,
            self.time_service,
            on_close=self._refresh_cases,
        )
        self.case_windows.append(window)
        window.show()

    # --- Admin-окна ---
    def _open_templates(self) -> None:
        if self.templates_window is None:
            self.templates_window = TemplatesCatalogWindow(self.session, is_admin=True)
        self.templates_window.show()
        self.templates_window.raise_()

    def _open_storage(self) -> None:
        if self.storage_window is None:
            self.storage_window = StorageLocationsWindow(self.session)
        self.storage_window.show()
        self.storage_window.raise_()

    def _open_timeline(self) -> None:
        if self.timeline_window is None:
            self.timeline_window = TimelineWindow(
                self.user,
                self.case_service,
                self.time_service,
                on_open_case=self._open_case_by_id,
            )
        self.timeline_window.show()
        self.timeline_window.raise_()
        self.timeline_window.refresh()

    def _open_stats(self) -> None:
        if self.stats_window is None:
            self.stats_window = StatsWindow(self.session)
        self.stats_window.show()
        self.stats_window.raise_()
        self.stats_window.refresh()

    def _open_calendar(self) -> None:
        if self.calendar_window is None:
            self.calendar_window = CalendarWindow(
                self.session,
                self.case_service,
                on_open_case=self._open_case_by_id,
            )
        self.calendar_window.show()
        self.calendar_window.raise_()
        self.calendar_window.refresh()

    def _open_inbox(self) -> None:
        if self.inbox_window is None:
            self.inbox_window = InboxWindow(self.session, self.case_service)
        self.inbox_window.show()
        self.inbox_window.raise_()

    def _open_backup(self) -> None:
        if self.backup_window is None:
            self.backup_window = BackupWindow(self.session, self.case_service)
        self.backup_window.show()
        self.backup_window.raise_()

    def _open_users(self) -> None:
        if self.users_window is None:
            self.users_window = UsersWindow(self.user, self.auth_service)
        self.users_window.show()
        self.users_window.raise_()

    def _restore_geometry(self) -> None:
        settings = QSettings("CaseWorkspace", "MainWindow")
        geom = settings.value("geometry")
        if geom is not None:
            self.restoreGeometry(geom)

    def closeEvent(self, event) -> None:
        settings = QSettings("CaseWorkspace", "MainWindow")
        settings.setValue("geometry", self.saveGeometry())
        # Закрываем дочерние окна
        try:
            for w in getattr(self, "case_windows", []):
                w.close()
            for w in (
                getattr(self, "users_window", None),
                getattr(self, "templates_window", None),
                getattr(self, "storage_window", None),
                getattr(self, "inbox_window", None),
                getattr(self, "backup_window", None),
                getattr(self, "timeline_window", None),
                getattr(self, "stats_window", None),
                getattr(self, "calendar_window", None),
                getattr(self, "bot_window", None),
                getattr(self, "notifications_window", None),
            ):
                if w is not None:
                    w.close()
        except Exception:
            pass
        super().closeEvent(event)

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+K"), self, self._on_search)
        QShortcut(QKeySequence("Ctrl+N"), self, self._new_case)
        QShortcut(QKeySequence("F5"), self, self._refresh_cases)
        QShortcut(QKeySequence("Ctrl+L"), self, self._lock_now)
        QShortcut(QKeySequence("Ctrl+Shift+T"), self, self._toggle_theme)

    def _on_search(self) -> None:
        dlg = GlobalSearchDialog(
            self.user, self.case_service, self.session,
            on_open_case=self._open_case_by_id, parent=self,
        )
        dlg.exec()

    def _on_idle_block(self) -> None:
        if self._lock_window is not None and self._lock_window.isVisible():
            return
        self._lock_now()

    def _lock_now(self) -> None:
        if self._lock_window is not None and self._lock_window.isVisible():
            return
        self._lock_window = LockWindow(self.auth_service, self.user, self)
        self._lock_window.unlocked.connect(self._on_unlocked)
        self._lock_window.show()
        self.hide()

    def _on_unlocked(self) -> None:
        self.show()
        self.raise_()
        self._lock_window = None
        self.idle_service.start()

    def _open_bot(self) -> None:
        if self.bot_window is None:
            self.bot_window = BotSettingsWindow("http://127.0.0.1:8765")
        self.bot_window.show()
        self.bot_window.raise_()
        self.bot_window._refresh_status()

    def _open_notifications(self) -> None:
        if self.notifications_window is None:
            self.notifications_window = NotificationsWindow(
                self.session, on_update_badge=self._update_notif_badge
            )
        self.notifications_window.show()
        self.notifications_window.raise_()
        self.notifications_window._refresh_all()

    def _update_notif_badge(self) -> None:
        if not hasattr(self, "btn_notifications"):
            return
        try:
            from case_workspace.auth_api.notifications import NotificationService
            count = len(NotificationService(self.session).list_unread())
        except Exception:
            return
        if count > 0:
            self.btn_notifications.setText(f"Уведомления ({count})")
            self.btn_notifications.setStyleSheet(
                "background-color: #DC2626; color: white; font-weight: 600;"
            )
        else:
            self.btn_notifications.setText("Уведомления")
            self.btn_notifications.setStyleSheet("")

    def _toggle_theme(self) -> None:
        from case_workspace.ui.theme_manager import theme_manager
        new = theme_manager.toggle()
        self.btn_theme.setText("☀" if new == "dark" else "🌙")

    def _logout(self) -> None:
        if QMessageBox.question(self, "Выход", "Выйти из программы?") != QMessageBox.Yes:
            return
        for w in self.case_windows:
            w.close()
        for w in (
            self.users_window,
            self.templates_window,
            self.storage_window,
            self.inbox_window,
            self.backup_window,
            self.timeline_window,
            self.stats_window,
        ):
            if w is not None:
                w.close()
        if self.on_logout:
            self.on_logout()
        self.close()
