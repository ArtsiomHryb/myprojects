"""Каталог шаблонов (бланков)."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
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

from case_workspace.templates.models import Template, TemplateCategory
from case_workspace.templates.service import TemplateService


class TemplatesCatalogWindow(QWidget):
    def __init__(self, session, is_admin: bool = True, parent=None) -> None:
        super().__init__(parent)
        self.session = session
        self.svc = TemplateService(session)
        self.is_admin = is_admin
        self._ids: list[int] = []
        self.setWindowTitle("Каталог бланков")
        self.setMinimumSize(750, 450)
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Каталог бланков")
        title.setObjectName("h1")
        header.addWidget(title)
        header.addStretch()
        if self.is_admin:
            self.btn_import = QPushButton("+ Импортировать DOCX")
            self.btn_import.setObjectName("primary")
            self.btn_import.clicked.connect(self._import)
            header.addWidget(self.btn_import)
            self.btn_scan = QPushButton("Сканировать resources/templates/")
            self.btn_scan.clicked.connect(self._scan)
            header.addWidget(self.btn_scan)
        root.addLayout(header)

        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск по названию…")
        self.search.textChanged.connect(self.refresh)
        filters.addWidget(self.search, 1)

        self.cat = QComboBox()
        self.cat.addItem("Все категории", None)
        for c in TemplateCategory:
            self.cat.addItem(c.label, c)
        self.cat.currentIndexChanged.connect(self.refresh)
        filters.addWidget(self.cat)
        root.addLayout(filters)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["★", "Название", "Категория", "Плейсхолдеров", "Авто"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self._toggle_favorite)
        root.addWidget(self.table)

        bar = QHBoxLayout()
        bar.addStretch()
        self.btn_fav = QPushButton("★ Избранное")
        self.btn_fav.clicked.connect(self._toggle_favorite)
        bar.addWidget(self.btn_fav)
        if self.is_admin:
            self.btn_delete = QPushButton("Удалить")
            self.btn_delete.clicked.connect(self._delete)
            bar.addWidget(self.btn_delete)
        self.btn_refresh = QPushButton("Обновить")
        self.btn_refresh.clicked.connect(self.refresh)
        bar.addWidget(self.btn_refresh)
        root.addLayout(bar)

    def refresh(self) -> None:
        category = self.cat.currentData()
        all_t = self.svc.list_templates(category)
        q = self.search.text().strip().lower()
        if q:
            all_t = [t for t in all_t if q in t.name.lower()]
        self.table.setRowCount(len(all_t))
        for row, t in enumerate(all_t):
            self.table.setItem(row, 0, QTableWidgetItem("★" if t.is_favorite else ""))
            self.table.setItem(row, 1, QTableWidgetItem(t.name))
            self.table.setItem(row, 2, QTableWidgetItem(t.category.label))
            try:
                schema = json.loads(t.fields_schema) if t.fields_schema else {}
                total = schema.get("total", 0)
                auto = schema.get("auto_mapped_count", 0)
            except ValueError:
                total, auto = 0, 0
            self.table.setItem(row, 3, QTableWidgetItem(str(total)))
            self.table.setItem(row, 4, QTableWidgetItem(f"{auto}/{total}"))
        self._ids = [t.id for t in all_t]

    def _selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._ids):
            return None
        return self._ids[row]

    def _import(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "Выберите DOCX-бланки", "", "Word (*.docx)"
        )
        if not files:
            return
        imported = 0
        errors: list[str] = []
        for f in files:
            try:
                self.svc.import_from_folder(Path(f))
                imported += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{Path(f).name}: {exc}")
        self.refresh()
        msg = f"Импортировано: {imported}"
        if errors:
            msg += "\n\nОшибки:\n" + "\n".join(errors[:10])
        QMessageBox.information(self, "Импорт", msg)

    def _scan(self) -> None:
        try:
            imported = self.svc.scan_all()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка", str(exc))
            return
        self.refresh()
        QMessageBox.information(self, "Сканирование", f"Найдено и импортировано: {len(imported)}")

    def _toggle_favorite(self) -> None:
        tid = self._selected_id()
        if tid is None:
            QMessageBox.information(self, "Избранное", "Выберите бланк.")
            return
        try:
            self.svc.toggle_favorite(tid)
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        self.refresh()

    def _delete(self) -> None:
        tid = self._selected_id()
        if tid is None:
            QMessageBox.information(self, "Удаление", "Выберите бланк.")
            return
        if QMessageBox.question(self, "Удаление", "Удалить бланк?") != QMessageBox.Yes:
            return
        self.svc.delete(tid)
        self.refresh()
