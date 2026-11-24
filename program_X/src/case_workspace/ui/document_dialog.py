"""Диалог создания документа из бланка (intake + рендер)."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from case_workspace.documents.services import DocumentService
from case_workspace.participants.service import PartyService
from case_workspace.templates.models import Template
from case_workspace.templates.service import TemplateService


class DocumentDialog(QDialog):
    def __init__(
        self,
        case_id: int,
        template: Template,
        template_service: TemplateService,
        document_service: DocumentService,
        party_service: PartyService,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.case_id = case_id
        self.template = template
        self.templates = template_service
        self.documents = document_service
        self.parties = party_service
        self.created_doc_id: int | None = None

        self.setWindowTitle(f"Новый документ — {template.name}")
        self.setMinimumSize(600, 550)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel(f"Формирование документа: {self.template.name}")
        title.setObjectName("h1")
        title.setWordWrap(True)
        root.addWidget(title)

        sub = QLabel(
            "Автозаполненные поля берутся из дела и профиля. "
            "Поля «ручной ввод» нужно заполнить вручную."
        )
        sub.setObjectName("caption")
        sub.setWordWrap(True)
        root.addWidget(sub)

        # Выбор фигуранта
        party_row = QHBoxLayout()
        party_row.addWidget(QLabel("Фигурант:"))
        self.party = QComboBox()
        self.party.addItem("— не выбирать —", None)
        for p in self.parties.list_parties(self.case_id):
            self.party.addItem(f"{p.role.label}: {p.full_name}", p.id)
        party_row.addWidget(self.party, 1)
        root.addLayout(party_row)

        # Скролл-форма
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.form = QFormLayout(container)
        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        schema = self.templates.get_fields_schema(self.template.id)
        self._custom_inputs: dict[str, QLineEdit] = {}
        preview_ctx = self.documents.build_context(self.case_id)

        for field in schema.get("fields", []):
            name = field["field"]
            source = field.get("source", "manual")
            if field.get("auto_mapped"):
                value = self._extract_from_context(preview_ctx, name)
                line = QLineEdit(str(value))
                line.setReadOnly(True)
                line.setStyleSheet("background-color: #F1F3F5;")
            else:
                line = QLineEdit()
                line.setPlaceholderText("Введите значение")
                self._custom_inputs[name] = line
            label_text = field.get("description") or name
            self.form.addRow(f"{label_text}:", line)

        if not schema.get("fields"):
            self.form.addRow(QLabel("В шаблоне не найдено плейсхолдеров."))

        # Кнопки
        buttons = QDialogButtonBox()
        self.btn_render = buttons.addButton(
            "Сформировать", QDialogButtonBox.AcceptRole
        )
        self.btn_render.setObjectName("primary")
        btn_cancel = buttons.addButton("Отмена", QDialogButtonBox.RejectRole)
        self.btn_render.clicked.connect(self._on_render)
        btn_cancel.clicked.connect(self.reject)
        root.addWidget(buttons)

    def _extract_from_context(self, ctx: dict, dotted: str):
        node = ctx
        for part in dotted.split("."):
            if isinstance(node, dict):
                node = node.get(part, "")
            else:
                return ""
        return node if node is not None else ""

    def _on_render(self) -> None:
        extra: dict = {}
        for name, line in self._custom_inputs.items():
            extra[name] = line.text().strip()

        try:
            doc = self.documents.render(
                self.template.id,
                self.case_id,
                party_id=self.party.currentData(),
                extra_data=extra,
                convert_to_pdf=True,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка", f"Не удалось сформировать: {exc}")
            return

        self.created_doc_id = doc.id
        paths = json.loads(doc.file_paths) if doc.file_paths else {}
        docx_path = paths.get("local_docx", "")
        pdf_path = paths.get("local_pdf", "")

        msg = QMessageBox(self)
        msg.setWindowTitle("Документ сформирован")
        info_lines = ["Документ создан успешно."]
        if docx_path:
            info_lines.append(f"DOCX: {Path(docx_path).name}")
        if pdf_path:
            info_lines.append(f"PDF: {Path(pdf_path).name}")
        else:
            info_lines.append("PDF: не удалось конвертировать (Word не установлен?)")
        msg.setText("\n".join(info_lines))
        open_btn = msg.addButton("Открыть", QMessageBox.AcceptRole)
        msg.addButton("Закрыть", QMessageBox.RejectRole)
        msg.exec()
        if msg.clickedButton() == open_btn:
            target = pdf_path or docx_path
            if target and Path(target).exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(target))
        self.accept()
