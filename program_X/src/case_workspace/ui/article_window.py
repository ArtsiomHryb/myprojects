"""Окно правовой справки по статье УК."""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from case_workspace.legal.service import LegalService


class ArticleWindow(QDialog):
    def __init__(
        self, code: str, part: str, legal_service: LegalService, parent=None
    ) -> None:
        super().__init__(parent)
        self.code = code
        self.part = part
        self.legal = legal_service
        self.setWindowTitle(f"Статья {code} ч.{part} УК РБ")
        self.setMinimumSize(650, 550)
        self._build()
        self._load()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(10)

        title_text = f"Статья {self.code}"
        if self.part:
            title_text += f", часть {self.part}"
        title_text += " УК Республики Беларусь"
        title = QLabel(title_text)
        title.setObjectName("h1")
        title.setWordWrap(True)
        root.addWidget(title)

        hint = QLabel(
            "Текст статьи хранится в кэше. Если его нет — откройте поиск в интернете, "
            "скопируйте текст и сохраните в программу."
        )
        hint.setObjectName("caption")
        hint.setWordWrap(True)
        root.addWidget(hint)

        root.addWidget(QLabel("Текст статьи:"))
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(
            "Вставьте текст статьи сюда (можно скопировать из pravo.by)"
        )
        root.addWidget(self.text_edit, 1)

        root.addWidget(QLabel("Комментарий / заметка:"))
        self.comment_edit = QTextEdit()
        self.comment_edit.setMaximumHeight(120)
        self.comment_edit.setPlaceholderText("Ваши заметки, ссылки на источники")
        root.addWidget(self.comment_edit)

        # Кнопки поиска
        search_row = QHBoxLayout()
        btn_find = QPushButton("🌐 Найти текст в интернете")
        btn_find.clicked.connect(self._open_search_text)
        search_row.addWidget(btn_find)

        btn_comment = QPushButton("💬 Найти комментарии")
        btn_comment.clicked.connect(self._open_search_comments)
        search_row.addWidget(btn_comment)

        btn_pravo = QPushButton("📖 Открыть pravo.by")
        btn_pravo.clicked.connect(self._open_pravo_by)
        search_row.addWidget(btn_pravo)

        search_row.addStretch()
        root.addLayout(search_row)

        # Кнопки действий
        action_row = QHBoxLayout()
        action_row.addStretch()
        self.btn_save = QPushButton("💾 Сохранить в кэш")
        self.btn_save.setObjectName("primary")
        self.btn_save.clicked.connect(self._save)
        action_row.addWidget(self.btn_save)

        self.btn_delete = QPushButton("Удалить из кэша")
        self.btn_delete.clicked.connect(self._delete)
        action_row.addWidget(self.btn_delete)

        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.reject)
        action_row.addWidget(btn_close)
        root.addLayout(action_row)

    def _load(self) -> None:
        cached = self.legal.get(self.code, self.part)
        if cached is None:
            return
        self.text_edit.setPlainText(cached.text)
        self.comment_edit.setPlainText(cached.comment)
        if cached.updated_at:
            self.setWindowTitle(
                f"Статья {self.code} ч.{self.part} УК РБ "
                f"(обновлено {cached.updated_at:%d.%m.%Y})"
            )

    def _open_search_text(self) -> None:
        url = self.legal.build_article_search_url(self.code, self.part)
        QDesktopServices.openUrl(QUrl(url))

    def _open_search_comments(self) -> None:
        url = self.legal.build_comment_search_url(self.code, self.part)
        QDesktopServices.openUrl(QUrl(url))

    def _open_pravo_by(self) -> None:
        QDesktopServices.openUrl(QUrl(self.legal.build_pravo_by_url()))

    def _save(self) -> None:
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Сохранение", "Введите или вставьте текст статьи.")
            return
        try:
            self.legal.save(
                self.code,
                self.part,
                text,
                comment=self.comment_edit.toPlainText().strip(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        QMessageBox.information(self, "Сохранено", "Статья сохранена в кэш.")
        self.accept()

    def _delete(self) -> None:
        if (
            QMessageBox.question(
                self, "Удаление", "Удалить статью из кэша?"
            ) != QMessageBox.Yes
        ):
            return
        self.legal.delete(self.code, self.part)
        self.text_edit.clear()
        self.comment_edit.clear()
        QMessageBox.information(self, "Удалено", "Статья удалена из кэша.")
