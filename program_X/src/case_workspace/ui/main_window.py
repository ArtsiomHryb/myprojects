"""Главное окно (заглушка этапа 1)."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget

from case_workspace.db.models import UserAccount


class MainWindow(QMainWindow):
    def __init__(self, user: UserAccount) -> None:
        super().__init__()
        self.user = user
        self.setWindowTitle("Case Workspace")
        self.setMinimumSize(1000, 700)
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setSpacing(12)

        title = QLabel(f"Добро пожаловать, {self.user.full_name or self.user.login}")
        title.setObjectName("h1")
        layout.addWidget(title)

        role = QLabel(f"Роль: {self.user.role.value}")
        role.setObjectName("caption")
        layout.addWidget(role)

        info = QLabel(
            "Рабочий стол (иконки дел, тайминг, документы) будет реализован "
            "на этапах 2+. На этом шаге работает:\n"
            "• регистрация администратора\n"
            "• вход по паролю\n"
            "• блокировка после 5 неудачных попыток (1 → 5 → 15 → 45 → 120 мин)\n"
            "• роли Admin / User"
        )
        info.setObjectName("hint")
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addStretch()
        self.setCentralWidget(central)