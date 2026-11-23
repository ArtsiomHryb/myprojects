"""Вкладка криптокошельков."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
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

from case_workspace.crypto.models import CryptoNetwork
from case_workspace.crypto.services import CryptoService
from case_workspace.crypto.validators import detect_network
from case_workspace.participants.service import PartyService


class _WalletDialog(QDialog):
    def __init__(self, case_id, crypto_service, party_service, parent=None):
        super().__init__(parent)
        self.case_id = case_id
        self.crypto = crypto_service
        self.party_service = party_service
        self.created = None
        self.setWindowTitle("Новый криптокошелёк")
        self.setMinimumWidth(560)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        title = QLabel("Добавление криптокошелька")
        title.setObjectName("h1")
        root.addWidget(title)

        form = QFormLayout()

        self.address = QLineEdit()
        self.address.setPlaceholderText(
            "bc1q… | 0x… | T… | UQ… | ltc1… | D…"
        )
        self.address.textChanged.connect(self._on_address)
        form.addRow("Адрес:", self.address)

        self.network = QComboBox()
        for n in CryptoNetwork:
            self.network.addItem(n.label, n)
        form.addRow("Сеть:", self.network)

        self.token = QLineEdit()
        self.token.setPlaceholderText("USDT, USDC … (опционально)")
        form.addRow("Токен:", self.token)

        self.party = QComboBox()
        self.party.addItem("— не привязан —", None)
        for p in self.party_service.list_parties(self.case_id):
            self.party.addItem(f"{p.role.label}: {p.full_name}", p.id)
        form.addRow("Участник:", self.party)

        self.label = QLineEdit()
        form.addRow("Метка:", self.label)

        self.comment = QLineEdit()
        form.addRow("Комментарий:", self.comment)

        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Добавить")
        buttons.button(QDialogButtonBox.Ok).setObjectName("primary")
        buttons.accepted.connect(self._on_add)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _on_address(self):
        addr = self.address.text().strip()
        if not addr:
            return
        network, _alternatives = detect_network(addr)
        if network != CryptoNetwork.OTHER:
            idx = self.network.findData(network)
            if idx >= 0:
                self.network.setCurrentIndex(idx)

    def _on_add(self):
        try:
            w = self.crypto.add_wallet(
                self.case_id,
                self.address.text(),
                network=self.network.currentData(),
                party_id=self.party.currentData(),
                token_symbol=self.token.text(),
                label=self.label.text(),
                comment=self.comment.text(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        self.created = w
        self.accept()


class CryptoWalletsTab(QWidget):
    def __init__(self, case_id, crypto_service, party_service, parent=None):
        super().__init__(parent)
        self.case_id = case_id
        self.crypto = crypto_service
        self.party_service = party_service
        self._ids = []
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(8)

        bar = QHBoxLayout()
        self.btn_add = QPushButton("+ Добавить кошелёк")
        self.btn_add.setObjectName("primary")
        self.btn_add.clicked.connect(self._add)
        bar.addWidget(self.btn_add)

        self.btn_delete = QPushButton("Удалить")
        self.btn_delete.clicked.connect(self._delete)
        bar.addWidget(self.btn_delete)

        bar.addStretch()
        self.summary = QLabel("")
        self.summary.setObjectName("caption")
        bar.addWidget(self.summary)
        root.addLayout(bar)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Сеть", "Адрес", "Токен", "Участник", "Метка"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        root.addWidget(self.table)

    def refresh(self):
        wallets = self.crypto.list_wallets(self.case_id)
        parties = {p.id: p for p in self.party_service.list_parties(self.case_id)}
        self.table.setRowCount(len(wallets))
        for row, w in enumerate(wallets):
            self.table.setItem(row, 0, QTableWidgetItem(w.network_enum.label))
            self.table.setItem(row, 1, QTableWidgetItem(w.address))
            self.table.setItem(row, 2, QTableWidgetItem(w.token_symbol or "—"))
            party = parties.get(w.party_id)
            self.table.setItem(
                row, 3, QTableWidgetItem(party.full_name if party else "—")
            )
            self.table.setItem(row, 4, QTableWidgetItem(w.label or "—"))
        self._ids = [w.id for w in wallets]
        self.summary.setText(f"Кошельков: {len(wallets)}")

    def _add(self):
        dlg = _WalletDialog(self.case_id, self.crypto, self.party_service, self)
        if dlg.exec() and dlg.created:
            self.refresh()

    def _delete(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._ids):
            QMessageBox.information(self, "Удаление", "Выберите кошелёк.")
            return
        if QMessageBox.question(
            self, "Удаление", "Удалить выбранный кошелёк?"
        ) != QMessageBox.Yes:
            return
        self.crypto.delete_wallet(self._ids[row])
        self.refresh()
