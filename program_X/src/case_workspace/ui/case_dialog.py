"""Диалог создания дела."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
)

from case_workspace.db.models import UserAccount
from case_workspace.projects.service import CaseService


class CaseDialog(QDialog):
    def __init__(self, user: UserAccount, service: CaseService, parent=None) -> None:
        super().__init__(parent)
        self.user = user
        self.service = service
        self.created_case_id: int | None = None

        self.setWindowTitle("Новое дело")
        self.setMinimumWidth(520)
        self._build_ui()
        self._update_number_preview()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel("Создание нового дела")
        title.setObjectName("h1")
        root.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        # --- Номер дела: год (авто) + орган (из профиля) + код (из профиля) ---
        info = QLabel(
            f"Год: {date.today().year % 100:02d}   "
            f"Орган: {self.user.organ_code or '—'}   "
            f"Код органа: {self.user.territorial_code or '—'}"
        )
        info.setObjectName("caption")
        form.addRow("Реквизиты:", info)

        self.sequential = QLineEdit()
        self.sequential.setMaxLength(4)
        self.sequential.setPlaceholderText("0001")
        self.sequential.textChanged.connect(self._update_number_preview)
        form.addRow("Порядковый №:", self.sequential)

        self.number_preview = QLabel("—")
        self.number_preview.setObjectName("hint")
        form.addRow("Итоговый номер:", self.number_preview)

        # --- Статья ---
        self.article = QLineEdit()
        self.article.setPlaceholderText("205 ч.2")
        form.addRow("Статья УК:", self.article)

        # --- Дата возбуждения ---
        self.initiated = QLineEdit(date.today().strftime("%d.%m.%Y"))
        self.initiated.setPlaceholderText("ДД.ММ.ГГГГ")
        form.addRow("Возбуждено:", self.initiated)

        # --- Срок ---
        self.months = QSpinBox()
        self.months.setRange(1, 36)
        self.months.setValue(2)
        self.months.setSuffix(" мес.")
        form.addRow("Срок:", self.months)

        # --- Орган возбуждения ---
        self.agency = QLineEdit(self.user.organization_name or "")
        self.agency.setPlaceholderText("Орган, возбудивший дело")
        form.addRow("Орган:", self.agency)

        # --- Цвет-тег ---
        self.color = QLineEdit()
        self.color.setPlaceholderText("#4F46E5 (опционально)")
        self.color.setMaxLength(9)
        form.addRow("Цвет-тег:", self.color)

        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Создать")
        buttons.button(QDialogButtonBox.Ok).setObjectName("primary")
        buttons.button(QDialogButtonBox.Cancel).setText("Отмена")
        buttons.accepted.connect(self._on_create)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _update_number_preview(self) -> None:
        seq = (self.sequential.text() or "").strip().zfill(4)
        year = f"{date.today().year % 100:02d}"
        organ = self.user.organ_code or "??"
        code = self.user.territorial_code or "???"
        self.number_preview.setText(f"{year}{organ}{code}{seq}")

    def _parse_date(self, text: str) -> date:
        try:
            d, m, y = text.strip().split(".")
            return date(int(y), int(m), int(d))
        except (ValueError, AttributeError):
            raise ValueError("Дата должна быть в формате ДД.ММ.ГГГГ") from None

    def _on_create(self) -> None:
        try:
            initiated = self._parse_date(self.initiated.text())
            if not (self.sequential.text() or "").strip().isdigit():
                raise ValueError("Порядковый номер — 1–4 цифры.")
            if not self.article.text().strip():
                raise ValueError("Укажите статью УК.")
            case = self.service.create_case(
                self.user,
                article=self.article.text(),
                initiated_at=initiated,
                sequential_number=self.sequential.text().strip(),
                originating_agency=self.agency.text().strip() or None,
                total_period_months=self.months.value(),
                color_tag=self.color.text().strip(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать дело: {exc}")
            return

        self.created_case_id = case.id
        self.accept()