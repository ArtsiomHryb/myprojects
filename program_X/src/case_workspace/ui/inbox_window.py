"""Окно «Неразобранное» (Inbox)."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from case_workspace.inbox.models import InboxItem, InboxSource, InboxStatus
from case_workspace.inbox.service import InboxService
from case_workspace.projects.service import CaseService


class _DetailsDialog(QDialog):
    def __init__(self, item: InboxItem, service: InboxService, parent=None) -> None:
        super().__init__(parent)
        self.item = item
        self.service = service
        self.setWindowTitle(f"Inbox #{item.id} — {item.source.label}")
        self.setMinimumSize(760, 720)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(10)

        title = QLabel(f"Элемент #{self.item.id}")
        title.setObjectName("h1")
        root.addWidget(title)

        meta_lines = [
            f"Источник: {self.item.source.label}",
            f"Файл: {self.item.source_file or '—'}",
            f"Метод: {self.item.extract_method or '—'}",
            f"Получен: {self.item.received_at:%d.%m.%Y %H:%M}",
            f"Статус: {self.item.status.label}",
            f"Теги: {self.item.auto_tags or '—'}",
        ]
        for line in meta_lines:
            lbl = QLabel(line)
            lbl.setObjectName("caption")
            root.addWidget(lbl)

        # Сущности
        root.addWidget(QLabel("Извлечённые сущности:"))
        entities = self.service.get_entities(self.item)
        if entities:
            lines = []
            for k, v in entities.items():
                if v:
                    lines.append(f"{k}: {', '.join(str(x) for x in v)}")
            entities_text = "\n".join(lines) if lines else "—"
        else:
            entities_text = "—"
        self.entities_view = QTextEdit()
        self.entities_view.setReadOnly(True)
        self.entities_view.setPlainText(entities_text)
        self.entities_view.setMaximumHeight(160)
        root.addWidget(self.entities_view)

        # Гипотезы
        root.addWidget(QLabel("Гипотезы привязки:"))
        hypotheses = self.service.get_hypotheses(self.item)
        if hypotheses:
            hyp_lines = []
            for h in hypotheses:
                reasons = ", ".join(h.get("reasons", []))
                hyp_lines.append(
                    f"[{h.get('weight', '?')}] Дело {h.get('case_number', '')}: {reasons}"
                )
            hyp_text = "\n".join(hyp_lines)
        else:
            hyp_text = "Совпадений не найдено"
        self.hyp_view = QTextEdit()
        self.hyp_view.setReadOnly(True)
        self.hyp_view.setPlainText(hyp_text)
        self.hyp_view.setMaximumHeight(100)
        root.addWidget(self.hyp_view)

        # Оригинальный текст
        root.addWidget(QLabel("Извлечённый текст:"))
        self.text_view = QTextEdit()
        self.text_view.setReadOnly(True)
        self.text_view.setPlainText(self.item.raw_text[:5000])
        root.addWidget(self.text_view, 1)

        # Действия
        action = QHBoxLayout()
        action.addStretch()
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        action.addWidget(btn_close)
        root.addLayout(action)


class InboxWindow(QWidget):
    def __init__(self, session, case_service: CaseService, parent=None) -> None:
        super().__init__(parent)
        self.session = session
        self.cases = case_service
        self.service = InboxService(session)
        self._ids: list[int] = []
        self.setWindowTitle("Неразобранное")
        self.setMinimumSize(1000, 640)
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Неразобранное")
        title.setObjectName("h1")
        header.addWidget(title)
        header.addStretch()

        self.btn_upload = QPushButton("+ Загрузить файл")
        self.btn_upload.setObjectName("primary")
        self.btn_upload.clicked.connect(self._upload)
        header.addWidget(self.btn_upload)

        self.btn_paste = QPushButton("+ Вставить текст")
        self.btn_paste.clicked.connect(self._paste_text)
        header.addWidget(self.btn_paste)
        root.addLayout(header)

        hint = QLabel(
            "Файлы PDF/DOCX/XLSX/сканы автоматически распознаются — программа "
            "извлекает идентификаторы, ФИО, номера дел и предлагает привязку."
        )
        hint.setObjectName("caption")
        hint.setWordWrap(True)
        root.addWidget(hint)

        # Фильтр
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Статус:"))
        self.filter_status = QComboBox()
        self.filter_status.addItem("Все", None)
        for s in InboxStatus:
            self.filter_status.addItem(s.label, s)
        self.filter_status.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(self.filter_status)
        filter_row.addStretch()
        self.summary = QLabel("")
        self.summary.setObjectName("caption")
        filter_row.addWidget(self.summary)
        root.addLayout(filter_row)

        # Таблица
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["#", "Источник", "Файл", "Теги", "Гипотезы", "Статус"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self._details)
        root.addWidget(self.table)

        # Действия
        action = QHBoxLayout()
        self.btn_details = QPushButton("Детали")
        self.btn_details.clicked.connect(self._details)
        action.addWidget(self.btn_details)

        self.btn_attach = QPushButton("Привязать к делу")
        self.btn_attach.setObjectName("primary")
        self.btn_attach.clicked.connect(self._attach)
        action.addWidget(self.btn_attach)

        self.btn_ignore = QPushButton("Игнорировать")
        self.btn_ignore.clicked.connect(self._ignore)
        action.addWidget(self.btn_ignore)

        self.btn_delete = QPushButton("Удалить")
        self.btn_delete.clicked.connect(self._delete)
        action.addWidget(self.btn_delete)

        action.addStretch()
        self.btn_refresh = QPushButton("Обновить")
        self.btn_refresh.clicked.connect(self.refresh)
        action.addWidget(self.btn_refresh)
        root.addLayout(action)

    def refresh(self) -> None:
        status = self.filter_status.currentData()
        items = self.service.list_items(status)
        self.table.setRowCount(len(items))
        for row, it in enumerate(items):
            hyp = self.service.get_hypotheses(it)
            hyp_count = len(hyp)
            self.table.setItem(row, 0, QTableWidgetItem(str(it.id)))
            self.table.setItem(row, 1, QTableWidgetItem(it.source.label))
            self.table.setItem(row, 2, QTableWidgetItem(it.source_file or "—"))
            self.table.setItem(row, 3, QTableWidgetItem(it.auto_tags or "—"))
            self.table.setItem(
                row, 4, QTableWidgetItem(f"{hyp_count} совпадений" if hyp_count else "—")
            )
            self.table.setItem(row, 5, QTableWidgetItem(it.status.label))
        self._ids = [it.id for it in items]
        self.summary.setText(f"Элементов: {len(items)}")

    def _selected_item(self) -> InboxItem | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._ids):
            return None
        return self.service.get(self._ids[row])

    def _upload(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите файлы",
            "",
            "Документы (*.pdf *.docx *.xlsx *.xls *.png *.jpg *.jpeg *.tif *.tiff *.txt)",
        )
        if not files:
            return
        ok, errors = 0, []
        for f in files:
            try:
                self.service.add_from_file(Path(f))
                ok += 1
            except ValueError as exc:
                errors.append(f"{Path(f).name}: {exc}")
        self.refresh()
        msg = f"Загружено: {ok}"
        if errors:
            msg += "\n\nОшибки:\n" + "\n".join(errors[:10])
        QMessageBox.information(self, "Загрузка", msg)

    def _paste_text(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Вставить текст")
        dlg.setMinimumSize(600, 500)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("Вставьте текст для анализа:"))
        editor = QTextEdit()
        editor.setPlaceholderText("Скопируйте текст сюда (из документа, письма, …)")
        layout.addWidget(editor, 1)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_ok = QPushButton("Проанализировать")
        btn_ok.setObjectName("primary")
        btn_row.addWidget(btn_ok)
        btn_cancel = QPushButton("Отмена")
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

        def on_ok():
            text = editor.toPlainText().strip()
            if not text:
                QMessageBox.warning(dlg, "Ошибка", "Текст пуст.")
                return
            try:
                self.service.add_from_text(text, source=InboxSource.CLIPBOARD)
            except ValueError as exc:
                QMessageBox.warning(dlg, "Ошибка", str(exc))
                return
            dlg.accept()
            self.refresh()

        btn_ok.clicked.connect(on_ok)
        btn_cancel.clicked.connect(dlg.reject)
        dlg.exec()

    def _details(self) -> None:
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "Детали", "Выберите элемент.")
            return
        dlg = _DetailsDialog(item, self.service, self)
        dlg.exec()

    def _attach(self) -> None:
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "Привязка", "Выберите элемент.")
            return

        hypotheses = self.service.get_hypotheses(item)
        if hypotheses:
            choices = [
                f"Дело {h.get('case_number', '')} (id={h.get('case_id')}) "
                f"— {h.get('weight')}"
                for h in hypotheses
            ]
            from PySide6.QtWidgets import QInputDialog

            choice, ok = QInputDialog.getItem(
                self,
                "Привязка к делу",
                "Выберите гипотезу или введите ID дела вручную:",
                choices,
                0,
                True,
            )
            if not ok or not choice:
                return
            try:
                case_id = int(choice.split("id=")[1].split(")")[0])
            except (IndexError, ValueError):
                QMessageBox.warning(self, "Ошибка", "Не удалось определить ID дела.")
                return
        else:
            from PySide6.QtWidgets import QInputDialog

            case_number, ok = QInputDialog.getText(
                self, "Привязка", "Введите номер дела (11 цифр):"
            )
            if not ok or not case_number.strip():
                return
            from sqlalchemy import select

            from case_workspace.projects.models import Case

            case = self.session.scalar(
                select(Case).where(Case.case_number == case_number.strip())
            )
            if case is None:
                QMessageBox.warning(self, "Ошибка", "Дело не найдено.")
                return
            case_id = case.id

        try:
            self.service.attach_to_case(item.id, case_id)
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        QMessageBox.information(self, "Привязка", "Элемент привязан к делу.")
        self.refresh()

    def _ignore(self) -> None:
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "Игнорировать", "Выберите элемент.")
            return
        if QMessageBox.question(
            self, "Игнорировать", "Игнорировать выбранный элемент?"
        ) != QMessageBox.Yes:
            return
        self.service.ignore(item.id)
        self.refresh()

    def _delete(self) -> None:
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "Удаление", "Выберите элемент.")
            return
        if QMessageBox.question(
            self, "Удаление", "Удалить элемент безвозвратно?"
        ) != QMessageBox.Yes:
            return
        self.service.delete(item.id)
        self.refresh()
