"""Диалог создания новой учётной записи с экрана входа."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from case_workspace.auth.service import AuthService
from case_workspace.db.models import UserAccount
from case_workspace.domain import errors


class NewAccountDialog(QDialog):
    def __init__(self, auth: AuthService, parent=None) -> None:
        super().__init__(parent)
        self.auth = auth
        self.created: UserAccount | None = None
        self.setWindowTitle("Новая учётная запись")
        self.setMinimumWidth(540)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel("Создание учётной записи")
        title.setObjectName("h1")
        root.addWidget(title)

        hint = QLabel("Учётная запись будет создана с ролью «Пользователь».")
        hint.setObjectName("caption")
        hint.setWordWrap(True)
        root.addWidget(hint)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self.login = QLineEdit()
        self.full_name = QLineEdit()
        self.position = QLineEdit()
        self.rank = QLineEdit()
        self.org = QLineEdit()
        self.organ_code = QLineEdit()
        self.organ_code.setMaxLength(2)
        self.organ_code.setPlaceholderText("2 цифры")
        self.territorial_code = QLineEdit()
        self.territorial_code.setMaxLength(3)
        self.territorial_code.setPlaceholderText("3 цифры")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("от 6 до 26 символов")
        self.password2 = QLineEdit()
        self.password2.setEchoMode(QLineEdit.Password)

        form.addRow("Логин:", self.login)
        form.addRow("ФИО:", self.full_name)
        form.addRow("Должность:", self.position)
        form.addRow("Звание:", self.rank)
        form.addRow("Место работы:", self.org)
        form.addRow("Код органа:", self.organ_code)
        form.addRow("Территориальный код:", self.territorial_code)
        form.addRow("Пароль:", self.password)
        form.addRow("Повтор пароля:", self.password2)
        root.addLayout(form)

        hint2 = QLabel(
            "Требования к паролю: от 6 до 26 символов, минимум 2 заглавные, "
            "2 строчные, 1 цифра, 1 специальный символ."
        )
        hint2.setObjectName("hint")
        hint2.setWordWrap(True)
        root.addWidget(hint2)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Создать")
        buttons.button(QDialogButtonBox.Ok).setObjectName("primary")
        buttons.button(QDialogButtonBox.Cancel).setText("Отмена")
        buttons.accepted.connect(self._on_create)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _on_create(self) -> None:
        if self.password.text() != self.password2.text():
            QMessageBox.warning(self, "Ошибка", "Пароли не совпадают.")
            return
        try:
            user = self.auth.register_user(
                login=self.login.text(),
                password=self.password.text(),
                full_name=self.full_name.text(),
                position=self.position.text(),
                rank=self.rank.text(),
                organization_name=self.org.text(),
                organ_code=self.organ_code.text(),
                territorial_code=self.territorial_code.text(),
            )
        except errors.PasswordPolicyError as exc:
            QMessageBox.warning(self, "Политика пароля", str(exc))
            return
        except errors.AuthError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать: {exc}")
            return
        QMessageBox.information(
            self, "Готово",
            f"Учётная запись «{user.login}» создана. Войдите с новым паролем.",
        )
        self.created = user
        self.accept()
