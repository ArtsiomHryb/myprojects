"""Окно «Бэкап»: проверка локаций, экспорт дел, восстановление."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
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

from case_workspace.backup.service import BackupService
from case_workspace.documents.models import StorageLocation
from case_workspace.projects.service import CaseService


class BackupWindow(QWidget):
    def __init__(self, session, case_service: CaseService, parent=None) -> None:
        super().__init__(parent)
        self.session = session
        self.cases = case_service
        self.backup = BackupService(session)
        self.setWindowTitle("Бэкап")
        self.setMinimumSize(1000, 660)
        self._build()
        self._refresh_locations()
        self._refresh_cases()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        title = QLabel("Бэкап и восстановление")
        title.setObjectName("h1")
        root.addWidget(title)

        # --- Локации ---
        loc_title = QLabel("Локации хранения")
        loc_title.setStyleSheet("font-weight: 600; margin-top: 8px;")
        root.addWidget(loc_title)

        self.loc_table = QTableWidget(0, 3)
        self.loc_table.setHorizontalHeaderLabels(["Название", "Путь", "Последняя проверка"])
        self.loc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.loc_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.loc_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.loc_table.setMaximumHeight(160)
        root.addWidget(self.loc_table)

        loc_bar = QHBoxLayout()
        self.btn_check = QPushButton("Проверить все локации")
        self.btn_check.clicked.connect(self._check_locations)
        loc_bar.addWidget(self.btn_check)
        loc_bar.addStretch()
        root.addLayout(loc_bar)

        # --- Экспорт дела ---
        exp_title = QLabel("Экспорт дела в ZIP")
        exp_title.setStyleSheet("font-weight: 600; margin-top: 8px;")
        root.addWidget(exp_title)

        exp_row = QHBoxLayout()
        exp_row.addWidget(QLabel("Дело:"))
        self.case_combo = QComboBox()
        exp_row.addWidget(self.case_combo, 1)
        self.btn_export = QPushButton("Экспортировать в ZIP…")
        self.btn_export.setObjectName("primary")
        self.btn_export.clicked.connect(self._export_case)
        exp_row.addWidget(self.btn_export)
        root.addLayout(exp_row)

        # --- Восстановление ---
        rest_title = QLabel("Восстановление из ZIP")
        rest_title.setStyleSheet("font-weight: 600; margin-top: 8px;")
        root.addWidget(rest_title)

        rest_row = QHBoxLayout()
        self.btn_inspect = QPushButton("Открыть ZIP и посмотреть манифест…")
        self.btn_inspect.clicked.connect(self._inspect_zip)
        rest_row.addWidget(self.btn_inspect)

        self.btn_restore = QPushButton("Восстановить дело…")
        self.btn_restore.clicked.connect(self._restore_zip)
        rest_row.addWidget(self.btn_restore)
        rest_row.addStretch()
        root.addLayout(rest_row)

        root.addStretch()

    def _refresh_locations(self) -> None:
        locs = list(self.session.query(StorageLocation).order_by(StorageLocation.id))
        self.loc_table.setRowCount(len(locs))
        for row, l in enumerate(locs):
            self.loc_table.setItem(row, 0, QTableWidgetItem(l.label))
            self.loc_table.setItem(row, 1, QTableWidgetItem(l.path))
            check = "—"
            if l.last_check_at:
                check = (
                    f"{l.last_check_at:%d.%m.%Y %H:%M} "
                    f"({'OK' if l.last_check_ok else 'ошибка'})"
                )
            self.loc_table.setItem(row, 2, QTableWidgetItem(check))

    def _refresh_cases(self) -> None:
        self.case_combo.clear()
        all_cases = self.cases.list_cases(include_archived=True)
        for c in all_cases:
            self.case_combo.addItem(f"{c.case_number or '—'} — {c.article}", c.id)

    def _check_locations(self) -> None:
        results = self.backup.check_all_locations()
        self._refresh_locations()
        if not results:
            QMessageBox.information(self, "Проверка", "Нет настроенных локаций.")
            return
        lines = [f"[{'OK' if ok else 'FAIL'}] {msg}" for _, ok, msg in results]
        QMessageBox.information(self, "Проверка локаций", "\n".join(lines))

    def _export_case(self) -> None:
        case_id = self.case_combo.currentData()
        if case_id is None:
            QMessageBox.information(self, "Экспорт", "Нет дел.")
            return
        case_number = self.case_combo.currentText().split(" — ")[0]
        default_name = f"case_{case_number}_{datetime_stamp()}.zip"
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить ZIP", default_name, "ZIP (*.zip)"
        )
        if not path:
            return
        try:
            result = self.backup.export_case_zip(case_id, Path(path))
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        size_kb = result.stat().st_size // 1024
        QMessageBox.information(
            self,
            "Экспорт",
            f"Дело экспортировано:\n{result}\n({size_kb} КБ)",
        )

    def _inspect_zip(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Открыть ZIP", "", "ZIP (*.zip)")
        if not path:
            return
        try:
            manifest = self.backup.inspect_zip(Path(path))
        except (ValueError, Exception) as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        case = manifest.get("case", {})
        lines = [
            f"Дело: {case.get('case_number', '')}",
            f"Статья: {case.get('article', '')}",
            f"Возбуждено: {case.get('initiated_at', '')}",
            f"Срок: {case.get('current_deadline', '')}",
            f"Экспортировано: {manifest.get('exported_at', '')}",
            "",
            f"Участников: {len(manifest.get('parties', []))}",
            f"Документов: {len(manifest.get('documents', []))}",
        ]
        QMessageBox.information(self, "Манифест ZIP", "\n".join(lines))

    def _restore_zip(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Восстановить из ZIP", "", "ZIP (*.zip)")
        if not path:
            return
        if QMessageBox.question(
            self, "Восстановление",
            "Восстановить дело из ZIP?\n\nВосстанавливаются только метаданные "
            "дела и участников. Документы — позже.",
        ) != QMessageBox.Yes:
            return
        try:
            result = self.backup.restore_case_zip(Path(path))
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка", f"Не удалось восстановить: {exc}")
            return
        self._refresh_cases()
        QMessageBox.information(
            self,
            "Восстановлено",
            f"Создано дело {result['case_number']}\n"
            f"Участников: {result['parties_restored']}\n"
            f"Документов в архиве: {result['documents_in_archive']}\n\n"
            f"{result['note']}",
        )


def datetime_stamp() -> str:
    from datetime import datetime as dt

    return dt.now().strftime("%Y%m%d_%H%M")
