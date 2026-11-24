"""Окно настройки локаций хранения (только Admin)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
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

from case_workspace.documents.services import (
    add_storage_location,
    delete_storage_location,
    list_storage_locations,
)


class StorageLocationsWindow(QWidget):
    def __init__(self, session, parent=None) -> None:
        super().__init__(parent)
        self.session = session
        self._ids: list[int] = []
        self.setWindowTitle("Локации хранения")
        self.setMinimumSize(650, 400)
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        title = QLabel("Локации хранения документов")
        title.setObjectName("h1")
        root.addWidget(title)

        hint = QLabel(
            "Укажите 1 или 2 папки на диске. Документы будут автоматически копироваться "
            "во все включённые локации (бэкап)."
        )
        hint.setObjectName("caption")
        hint.setWordWrap(True)
        root.addWidget(hint)

        add_row = QHBoxLayout()
        self.label_input = QLineEdit()
        self.label_input.setPlaceholderText("Название (Основная / Резервная)")
        add_row.addWidget(self.label_input)

        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("/Users/…/Backup/Cases")
        add_row.addWidget(self.path_input, 1)

        self.btn_browse = QPushButton("Выбрать…")
        self.btn_browse.clicked.connect(self._browse)
        add_row.addWidget(self.btn_browse)

        self.btn_add = QPushButton("+ Добавить")
        self.btn_add.setObjectName("primary")
        self.btn_add.clicked.connect(self._add)
        add_row.addWidget(self.btn_add)
        root.addLayout(add_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Название", "Путь", "Включена", "Проверка"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        root.addWidget(self.table)

        bar = QHBoxLayout()
        bar.addStretch()
        self.btn_delete = QPushButton("Удалить")
        self.btn_delete.clicked.connect(self._delete)
        bar.addWidget(self.btn_delete)
        self.btn_refresh = QPushButton("Обновить")
        self.btn_refresh.clicked.connect(self.refresh)
        bar.addWidget(self.btn_refresh)
        root.addLayout(bar)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Выберите папку для бэкапа")
        if path:
            self.path_input.setText(path)
            if not self.label_input.text().strip():
                self.label_input.setText("Локация")

    def refresh(self) -> None:
        locs = list_storage_locations(self.session)
        self.table.setRowCount(len(locs))
        for row, l in enumerate(locs):
            self.table.setItem(row, 0, QTableWidgetItem(l.label))
            self.table.setItem(row, 1, QTableWidgetItem(l.path))
            self.table.setItem(row, 2, QTableWidgetItem("да" if l.enabled else "нет"))
            self.table.setItem(
                row, 3, QTableWidgetItem("OK" if l.last_check_ok else "нет папки")
            )
        self._ids = [l.id for l in locs]

    def _add(self) -> None:
        label = self.label_input.text().strip() or "Локация"
        path = self.path_input.text().strip()
        if not path:
            QMessageBox.warning(self, "Ошибка", "Укажите путь к папке.")
            return
        try:
            add_storage_location(self.session, label, path, enabled=True)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить: {exc}")
            return
        self.label_input.clear()
        self.path_input.clear()
        self.refresh()

    def _delete(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._ids):
            QMessageBox.information(self, "Удаление", "Выберите локацию.")
            return
        if QMessageBox.question(
            self, "Удаление", "Удалить выбранную локацию?"
        ) != QMessageBox.Yes:
            return
        delete_storage_location(self.session, self._ids[row])
        self.refresh()
