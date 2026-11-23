"""Диалог восстановления пароля (через Telegram-бот)."""

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout


class RecoverPasswordDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Восстановление пароля")
        self.setMinimumWidth(500)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel("Восстановление пароля")
        title.setObjectName("h1")
        root.addWidget(title)

        info = QLabel(
            "Восстановление пароля выполняется через Telegram-бот программы.\n\n"
            "Порядок действий:\n"
            "  1. Откройте Telegram-бот программы.\n"
            "  2. Отправьте команду /start.\n"
            "  3. Введите логин от учётной записи.\n"
            "  4. Ответьте на контрольный вопрос.\n"
            "  5. Получите новый временный пароль.\n\n"
            "⚠️ Функция Telegram-бота подключается на этапе 10.\n\n"
            "Если бот недоступен — обратитесь к администратору программы: "
            "он может сбросить пароль в разделе «Пользователи»."
        )
        info.setWordWrap(True)
        root.addWidget(info)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.button(QDialogButtonBox.Ok).setText("Понятно")
        buttons.button(QDialogButtonBox.Ok).setObjectName("primary")
        buttons.accepted.connect(self.accept)
        root.addWidget(buttons)
