"""Окно настроек Telegram-бота (только Admin)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import httpx
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from case_workspace.telegram_bot.config import BOT_TOKEN_FILE, load_bot_token, save_bot_token


class BotSettingsWindow(QWidget):
    def __init__(self, api_url: str, parent=None) -> None:
        super().__init__(parent)
        self.api_url = api_url
        self._process: subprocess.Popen | None = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_status)
        self._timer.start(5000)

        self.setWindowTitle("Telegram-бот")
        self.setMinimumSize(650, 450)
        self._build()
        self._refresh_status()
        self._load_token()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        title = QLabel("Управление Telegram-ботом")
        title.setObjectName("h1")
        root.addWidget(title)

        # API
        api_box = QGroupBox("Локальный API")
        api_layout = QVBoxLayout(api_box)
        self.api_status = QLabel("—")
        api_layout.addWidget(self.api_status)
        root.addWidget(api_box)

        # Токен
        token_box = QGroupBox("Токен бота")
        token_layout = QVBoxLayout(token_box)
        hint = QLabel(
            "Получите токен у @BotFather в Telegram. "
            f"Хранится в файле: {BOT_TOKEN_FILE}"
        )
        hint.setObjectName("caption")
        hint.setWordWrap(True)
        token_layout.addWidget(hint)

        row = QHBoxLayout()
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setPlaceholderText("1234567890:AAH...")
        row.addWidget(self.token_input, 1)
        self.btn_show = QPushButton("Показать")
        self.btn_show.setCheckable(True)
        self.btn_show.clicked.connect(self._toggle_token_visibility)
        row.addWidget(self.btn_show)
        token_layout.addLayout(row)

        btn_row = QHBoxLayout()
        self.btn_save = QPushButton("💾 Сохранить токен")
        self.btn_save.setObjectName("primary")
        self.btn_save.clicked.connect(self._save_token)
        btn_row.addWidget(self.btn_save)
        btn_row.addStretch()
        token_layout.addLayout(btn_row)
        root.addWidget(token_box)

        # Процесс
        proc_box = QGroupBox("Процесс бота")
        proc_layout = QVBoxLayout(proc_box)
        self.proc_status = QLabel("—")
        proc_layout.addWidget(self.proc_status)

        proc_btn = QHBoxLayout()
        self.btn_start = QPushButton("▶ Запустить бота")
        self.btn_start.setObjectName("primary")
        self.btn_start.clicked.connect(self._start_bot)
        proc_btn.addWidget(self.btn_start)

        self.btn_stop = QPushButton("⏹ Остановить")
        self.btn_stop.clicked.connect(self._stop_bot)
        proc_btn.addWidget(self.btn_stop)

        self.btn_refresh = QPushButton("🔄 Обновить статус")
        self.btn_refresh.clicked.connect(self._refresh_status)
        proc_btn.addWidget(self.btn_refresh)
        proc_btn.addStretch()
        proc_layout.addLayout(proc_btn)
        root.addWidget(proc_box)

        # Подсказка
        hint2 = QLabel(
            "💡 Бот работает в отдельном процессе и общается с API. "
            "При закрытии программы процесс бота завершается."
        )
        hint2.setObjectName("caption")
        hint2.setWordWrap(True)
        root.addWidget(hint2)

        root.addStretch()

    def _load_token(self) -> None:
        t = load_bot_token()
        if t:
            self.token_input.setText(t)

    def _toggle_token_visibility(self) -> None:
        if self.btn_show.isChecked():
            self.token_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_show.setText("Скрыть")
        else:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_show.setText("Показать")

    def _save_token(self) -> None:
        token = self.token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "Ошибка", "Токен пуст.")
            return
        if ":" not in token:
            QMessageBox.warning(self, "Ошибка", "Токен должен содержать ':'.")
            return
        try:
            save_bot_token(token)
        except OSError as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {exc}")
            return
        QMessageBox.information(self, "Сохранено", f"Токен сохранён:\n{BOT_TOKEN_FILE}")

    def _refresh_status(self) -> None:
        # API
        try:
            r = httpx.get(f"{self.api_url}/health", timeout=2)
            if r.status_code == 200:
                self.api_status.setText(f"✅ API доступен: {self.api_url}")
                self.api_status.setStyleSheet("color: #16A34A;")
            else:
                self.api_status.setText(f"⚠️ API ответил {r.status_code}")
                self.api_status.setStyleSheet("color: #CA8A04;")
        except Exception:
            self.api_status.setText(f"❌ API недоступен: {self.api_url}")
            self.api_status.setStyleSheet("color: #DC2626;")

        # Процесс
        if self._process is not None and self._process.poll() is None:
            self.proc_status.setText(f"▶ бот работает (PID {self._process.pid})")
            self.proc_status.setStyleSheet("color: #16A34A;")
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
        else:
            self._process = None
            self.proc_status.setText("⏹ бот остановлен")
            self.proc_status.setStyleSheet("color: #64748B;")
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)

    def _start_bot(self) -> None:
        if self._process is not None and self._process.poll() is None:
            QMessageBox.information(self, "Бот", "Бот уже запущен.")
            return

        token = load_bot_token()
        if not token:
            QMessageBox.warning(
                self, "Ошибка",
                "Сначала сохраните токен бота (см. раздел «Токен бота»).",
            )
            return

        try:
            self._process = subprocess.Popen(
                [sys.executable, "-m", "case_workspace.telegram_bot"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить бота: {exc}")
            return

        QMessageBox.information(
            self, "Бот",
            "Бот запущен в фоне.\n"
            "Откройте Telegram и отправьте /start своему боту."
        )
        self._refresh_status()

    def _stop_bot(self) -> None:
        if self._process is None or self._process.poll() is not None:
            return
        try:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
        except Exception as exc:
            QMessageBox.warning(self, "Ошибка", f"Не удалось остановить: {exc}")
        self._process = None
        self._refresh_status()

    def closeEvent(self, event) -> None:
        # При закрытии окна бот останавливается
        if self._process is not None and self._process.poll() is None:
            try:
                self._process.terminate()
                try:
                    self._process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self._process.kill()
            except Exception:
                pass
            self._process = None
        super().closeEvent(event)
