"""Рабочий стол с иконками дел."""

from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QAbstractItemView, QListView

from case_workspace.projects.models import Case


ICON_WIDTH = 200
ICON_HEIGHT = 160
GRID_WIDTH = 220
GRID_HEIGHT = 180


def _urgency_color(days_left: int | None) -> str:
    if days_left is None:
        return "#94A3B8"
    if days_left < 0:
        return "#991B1B"
    if days_left <= 14:
        return "#DC2626"
    if days_left <= 30:
        return "#EA580C"
    if days_left <= 60:
        return "#CA8A04"
    return "#16A34A"


def _fmt_short_name(full_name: str) -> str:
    parts = full_name.split()
    if len(parts) >= 3:
        return f"{parts[0]} {parts[1][0]}.{parts[2][0]}."
    if len(parts) == 2:
        return f"{parts[0]} {parts[1][0]}."
    return full_name


def make_case_icon(case: Case, days_left: int | None) -> QPixmap:
    pm = QPixmap(ICON_WIDTH, ICON_HEIGHT)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    p.setBrush(QColor("#FFFFFF"))
    p.setPen(QPen(QColor("#E5E7EB"), 1))
    p.drawRoundedRect(0, 0, ICON_WIDTH - 1, ICON_HEIGHT - 1, 12, 12)

    urgency = _urgency_color(days_left)
    p.setBrush(QColor(urgency))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(0, 0, 6, ICON_HEIGHT, 3, 3)

    p.setPen(QColor("#0F172A"))
    f = QFont()
    f.setPointSize(17)
    f.setBold(True)
    p.setFont(f)
    article = case.article or "—"
    p.drawText(QRect(18, 14, ICON_WIDTH - 40, 32), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, article)

    f = QFont("Menlo")
    f.setPointSize(10)
    p.setFont(f)
    p.setPen(QColor("#475569"))
    p.drawText(
        QRect(18, 50, ICON_WIDTH - 40, 20),
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
        case.case_number or "— эпизод —",
    )

    p.setPen(QPen(QColor("#E5E7EB"), 1))
    p.drawLine(18, 78, ICON_WIDTH - 18, 78)

    f = QFont()
    f.setPointSize(10)
    p.setFont(f)
    p.setPen(QColor("#0F172A"))
    accused = case.accused_name or "—"
    if len(accused) > 26:
        accused = accused[:24] + "…"
    p.drawText(
        QRect(18, 88, ICON_WIDTH - 40, 20),
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
        f"Обв: {_fmt_short_name(accused)}",
    )

    if case.victim_name:
        p.setPen(QColor("#475569"))
        victim = case.victim_name
        if len(victim) > 26:
            victim = victim[:24] + "…"
        p.drawText(
            QRect(18, 108, ICON_WIDTH - 40, 20),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            f"Пот: {_fmt_short_name(victim)}",
        )

    f = QFont()
    f.setPointSize(9)
    p.setFont(f)
    p.setPen(QColor("#64748B"))
    days_text = "—"
    if days_left is not None:
        if days_left < 0:
            days_text = f"просрочено на {abs(days_left)} дн."
        elif days_left == 0:
            days_text = "срок истекает сегодня"
        else:
            days_text = f"осталось {days_left} дн."
    p.drawText(
        QRect(18, ICON_HEIGHT - 26, ICON_WIDTH - 40, 20),
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
        days_text,
    )

    if case.color_tag and case.color_tag.startswith("#"):
        try:
            p.setBrush(QColor(case.color_tag))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(ICON_WIDTH - 22, 16, 12, 12)
        except Exception:  # noqa: BLE001
            pass

    p.end()
    return pm


class DesktopView(QListView):
    """Список иконок с drag-and-drop и снапом по сетке."""

    case_activated = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._model = QStandardItemModel(self)
        self.setModel(self._model)

        self.setViewMode(QListView.ViewMode.IconMode)
        self.setIconSize(QSize(ICON_WIDTH, ICON_HEIGHT))
        self.setGridSize(QSize(GRID_WIDTH, GRID_HEIGHT))
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setMovement(QListView.Movement.Snap)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSpacing(8)
        self.setUniformItemSizes(True)
        self.setWordWrap(True)
        self.doubleClicked.connect(self._on_double_clicked)
        self._case_ids: list[int] = []

    def _on_double_clicked(self, index) -> None:
        item = self._model.itemFromIndex(index)
        if item is None:
            return
        case_id = item.data(Qt.ItemDataRole.UserRole)
        if case_id:
            self.case_activated.emit(int(case_id))

    def populate(self, cases: list[tuple[Case, int | None]]) -> None:
        selected_id = None
        indexes = self.selectedIndexes()
        if indexes:
            cur = self._model.itemFromIndex(indexes[0])
            if cur is not None:
                selected_id = cur.data(Qt.ItemDataRole.UserRole)

        self._model.clear()
        self._case_ids = []
        for case, days_left in cases:
            pm = make_case_icon(case, days_left)
            item = QStandardItem()
            item.setEditable(False)
            item.setIcon(QIcon(pm))
            item.setData(case.id, Qt.ItemDataRole.UserRole)
            item.setToolTip(
                f"{case.article or ''}\n№ {case.case_number or ''}\n"
                f"Обв: {case.accused_name or '—'}\nПот: {case.victim_name or '—'}"
            )
            item.setSizeHint(QSize(ICON_WIDTH, ICON_HEIGHT))
            self._model.appendRow(item)
            self._case_ids.append(case.id)

        if selected_id is not None:
            for row in range(self._model.rowCount()):
                it = self._model.item(row)
                if it is not None and it.data(Qt.ItemDataRole.UserRole) == selected_id:
                    self.setCurrentIndex(self._model.index(row, 0))
                    break

    def selected_case_id(self) -> int | None:
        indexes = self.selectedIndexes()
        if not indexes:
            return None
        item = self._model.itemFromIndex(indexes[0])
        if item is None:
            return None
        val = item.data(Qt.ItemDataRole.UserRole)
        return int(val) if val else None

    def all_case_ids(self) -> list[int]:
        return list(self._case_ids)

    def current_order(self) -> list[tuple[int, int]]:
        pairs: list[tuple[int, int]] = []
        for row in range(self._model.rowCount()):
            item = self._model.item(row)
            if item is None:
                continue
            case_id = item.data(Qt.ItemDataRole.UserRole)
            if case_id is not None:
                pairs.append((int(case_id), row))
        return pairs
