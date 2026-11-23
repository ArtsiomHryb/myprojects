"""Вкладка документов в карточке дела."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
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

from case_workspace.documents.models import Document
from case_workspace.documents.services import DocumentService
from case_workspace.participants.service import PartyService
from case_workspace.templates.models import TemplateCategory
from case_workspace.templates.service import TemplateService
from case_workspace.ui.document_dialog import DocumentDialog


class _TemplatePicker(QDialog):
    def __init__(self, templates: list, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Выбор бланка")
        self.setMinimumSize(640, 500)
        self.templates = templates
        self.selected = None
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        title = QLabel("Выберите бланк")
        title.setObjectName("h1")
        root.addWidget(title)

        self.search = QComboBox()
        self.search.setEditable(True)
        self.search.addItem("Все", None)
        for c in TemplateCategory:
            self.search.addItem(c.label, c)
        root.addWidget(self.search)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["★", "Название", "Категория"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self._on_ok)
        root.addWidget(self.table, 1)

        bar = QHBoxLayout()
        bar.addStretch()
        btn_ok = QPushButton("Выбрать")
        btn_ok.setObjectName("primary")
        btn_ok.clicked.connect(self._on_ok)
        bar.addWidget(btn_ok)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        bar.addWidget(btn_cancel)
        root.addLayout(bar)

        self._ids: list[int] = []
        self._refresh()

    def _refresh(self) -> None:
        self.table.setRowCount(len(self.templates))
        for row, t in enumerate(self.templates):
            self.table.setItem(row, 0, QTableWidgetItem("★" if t.is_favorite else ""))
            self.table.setItem(row, 1, QTableWidgetItem(t.name))
            self.table.setItem(row, 2, QTableWidgetItem(t.category.label))
        self._ids = [t.id for t in self.templates]

    def _on_ok(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._ids):
            QMessageBox.information(self, "Выбор", "Выберите бланк.")
            return
        self.selected = self._ids[row]
        self.accept()


class DocumentsTab(QWidget):
    def __init__(
        self,
        case_id: int,
        document_service: DocumentService,
        template_service: TemplateService,
        party_service: PartyService,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.case_id = case_id
        self.documents = document_service
        self.templates = template_service
        self.parties = party_service
        self._ids: list[int] = []
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(8)

        bar = QHBoxLayout()
        self.btn_create = QPushButton("+ Создать документ")
        self.btn_create.setObjectName("primary")
        self.btn_create.clicked.connect(self._create)
        bar.addWidget(self.btn_create)

        self.btn_open = QPushButton("Открыть")
        self.btn_open.clicked.connect(self._open)
        bar.addWidget(self.btn_open)

        self.btn_versions = QPushButton("Версии")
        self.btn_versions.clicked.connect(self._show_versions)
        bar.addWidget(self.btn_versions)

        self.btn_delete = QPushButton("Удалить")
        self.btn_delete.clicked.connect(self._delete)
        bar.addWidget(self.btn_delete)

        bar.addStretch()
        self.summary = QLabel("")
        self.summary.setObjectName("caption")
        bar.addWidget(self.summary)
        root.addLayout(bar)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Название", "Тип", "Статус", "Версия", "Создан"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self._open)
        root.addWidget(self.table)

    def refresh(self) -> None:
        docs = self.documents.list_documents(self.case_id)
        self.table.setRowCount(len(docs))
        for row, d in enumerate(docs):
            self.table.setItem(row, 0, QTableWidgetItem(d.title))
            self.table.setItem(row, 1, QTableWidgetItem(d.doc_type.value))
            self.table.setItem(row, 2, QTableWidgetItem(d.status.label))
            self.table.setItem(row, 3, QTableWidgetItem(f"v{d.version}"))
            self.table.setItem(
                row, 4, QTableWidgetItem(d.created_at.strftime("%d.%m.%Y %H:%M"))
            )
        self._ids = [d.id for d in docs]
        self.summary.setText(f"Документов: {len(docs)}")

    def _selected_doc(self) -> Document | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._ids):
            return None
        return self.documents.get(self._ids[row])

    def _create(self) -> None:
        tpls = self.templates.list_templates()
        if not tpls:
            QMessageBox.information(
                self, "Нет бланков",
                "В каталоге нет ни одного бланка. Откройте «Каталог бланков» "
                "и импортируйте DOCX-файлы.",
            )
            return
        picker = _TemplatePicker(tpls, self)
        if not picker.exec() or picker.selected is None:
            return
        template = self.templates.get(picker.selected)
        if template is None:
            return
        dlg = DocumentDialog(
            self.case_id, template, self.templates, self.documents, self.parties, self
        )
        if dlg.exec() and dlg.created_doc_id:
            self.refresh()

    def _open(self) -> None:
        doc = self._selected_doc()
        if doc is None:
            QMessageBox.information(self, "Открыть", "Выберите документ.")
            return
        paths = json.loads(doc.file_paths) if doc.file_paths else {}
        target = paths.get("local_pdf") or paths.get("local_docx")
        if not target or not Path(target).exists():
            QMessageBox.warning(self, "Открыть", "Файл не найден на диске.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(target))

    def _show_versions(self) -> None:
        doc = self._selected_doc()
        if doc is None:
            QMessageBox.information(self, "Версии", "Выберите документ.")
            return
        versions = self.documents.list_versions(doc.id)
        lines = [f"Документ: {doc.title}"]
        for v in versions:
            lines.append(
                f"  v{v.version} — {v.created_at:%d.%m.%Y %H:%M} — {v.change_reason}"
            )
            lines.append(f"    {v.file_path}")
            if v.pdf_path:
                lines.append(f"    {v.pdf_path}")
        QMessageBox.information(self, "Версии документа", "\n".join(lines))

    def _delete(self) -> None:
        doc = self._selected_doc()
        if doc is None:
            QMessageBox.information(self, "Удаление", "Выберите документ.")
            return
        if QMessageBox.question(
            self, "Удаление", f"Удалить документ «{doc.title}»?"
        ) != QMessageBox.Yes:
            return
        self.documents.delete(doc.id)
        self.refresh()
