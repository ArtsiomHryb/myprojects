"""Окно статистики с графиками (matplotlib)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from case_workspace.statistics.service import StatsService
from case_workspace.timetracking.service import TimeService

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure

    HAS_MPL = True
except Exception:  # noqa: BLE001
    HAS_MPL = False


def _fmt_hours(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return f"{h} ч {m:02d} мин"


class _StatTile(QWidget):
    def __init__(self, title: str, value: str, color: str = "#4F46E5") -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(
            f"font-size: 28px; font-weight: 700; color: {color};"
        )
        layout.addWidget(self.value_label)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("caption")
        layout.addWidget(self.title_label)


class StatsWindow(QWidget):
    def __init__(self, session, parent=None) -> None:
        super().__init__(parent)
        self.session = session
        self.service = StatsService(session)
        self.setWindowTitle("Статистика")
        self.setMinimumSize(900, 600)
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Статистика")
        title.setObjectName("h1")
        header.addWidget(title)
        header.addStretch()
        self.btn_refresh = QPushButton("Обновить")
        self.btn_refresh.clicked.connect(self.refresh)
        header.addWidget(self.btn_refresh)
        root.addLayout(header)

        # Плитки
        tiles_row = QHBoxLayout()
        self.tile_total = _StatTile("Всего дел", "—")
        self.tile_active = _StatTile("Активных", "—", "#16A34A")
        self.tile_overdue = _StatTile("Просрочено", "—", "#DC2626")
        self.tile_time = _StatTile("Общее время", "—", "#4F46E5")
        for t in (self.tile_total, self.tile_active, self.tile_overdue, self.tile_time):
            tiles_row.addWidget(t)
        root.addLayout(tiles_row)

        # Вкладки с графиками
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        self.tab_articles = self._make_plot_tab("Дела по статьям")
        self.tab_urgency = self._make_plot_tab("Распределение по срочности")
        self.tab_load = self._make_plot_tab("Нагрузка по делам (топ-20)")
        self.tab_months = self._make_plot_tab("Динамика по месяцам")

        self.tabs.addTab(self.tab_articles, "По статьям")
        self.tabs.addTab(self.tab_urgency, "По срочности")
        self.tabs.addTab(self.tab_load, "Нагрузка")
        self.tabs.addTab(self.tab_months, "По месяцам")

        if not HAS_MPL:
            hint = QLabel(
                "⚠️ matplotlib не установлен. Установите: pip install -e \".[dev]\""
            )
            hint.setObjectName("danger")
            root.addWidget(hint)

    def _make_plot_tab(self, title: str) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        label = QLabel(title)
        label.setStyleSheet("font-weight: 600;")
        layout.addWidget(label)
        if HAS_MPL:
            fig = Figure(figsize=(9, 5), tight_layout=True)
            canvas = FigureCanvas(fig)
            layout.addWidget(canvas, 1)
            w.figure = fig  # type: ignore[attr-defined]
            w.canvas = canvas  # type: ignore[attr-defined]
        else:
            placeholder = QLabel("График недоступен (matplotlib не установлен).")
            placeholder.setObjectName("hint")
            layout.addWidget(placeholder, 1)
        return w

    def refresh(self) -> None:
        summary = self.service.summary()
        self.tile_total.value_label.setText(str(summary["total"]))
        self.tile_active.value_label.setText(str(summary["active"]))
        self.tile_overdue.value_label.setText(str(summary["overdue"]))
        self.tile_time.value_label.setText(_fmt_hours(summary["total_seconds"]))

        if not HAS_MPL:
            return

        self._draw_articles()
        self._draw_urgency()
        self._draw_load()
        self._draw_months()

    def _clear_fig(self, widget: QWidget) -> "Figure | None":
        if not hasattr(widget, "figure"):
            return None
        fig = widget.figure  # type: ignore[attr-defined]
        fig.clear()
        return fig

    def _draw_articles(self) -> None:
        fig = self._clear_fig(self.tab_articles)
        if fig is None:
            return
        data = self.service.cases_by_article()
        ax = fig.add_subplot(111)
        if not data:
            ax.text(0.5, 0.5, "Нет данных", ha="center", va="center")
            ax.axis("off")
        else:
            labels = list(data.keys())
            values = list(data.values())
            ax.barh(range(len(labels)), values, color="#4F46E5")
            ax.set_yticks(range(len(labels)))
            ax.set_yticklabels(labels)
            ax.set_xlabel("Количество дел")
            ax.invert_yaxis()
        fig.canvas.draw_idle()  # type: ignore[attr-defined]

    def _draw_urgency(self) -> None:
        fig = self._clear_fig(self.tab_urgency)
        if fig is None:
            return
        data = self.service.cases_by_urgency()
        colors = ["#991B1B", "#DC2626", "#CA8A04", "#16A34A"]
        ax = fig.add_subplot(111)
        non_zero = [(k, v) for k, v in data.items() if v > 0]
        if not non_zero:
            ax.text(0.5, 0.5, "Нет данных", ha="center", va="center")
            ax.axis("off")
        else:
            labels = [k for k, _ in non_zero]
            values = [v for _, v in non_zero]
            idx = [list(data.keys()).index(k) for k in labels]
            c = [colors[i] for i in idx]
            ax.pie(
                values,
                labels=labels,
                colors=c,
                autopct="%1.0f%%",
                startangle=90,
            )
        fig.canvas.draw_idle()  # type: ignore[attr-defined]

    def _draw_load(self) -> None:
        fig = self._clear_fig(self.tab_load)
        if fig is None:
            return
        data = self.service.load_by_case(limit=20)
        ax = fig.add_subplot(111)
        if not data:
            ax.text(0.5, 0.5, "Нет данных", ha="center", va="center")
            ax.axis("off")
        else:
            labels = [d[0] for d in data]
            hours = [d[1] / 3600 for d in data]
            ax.barh(range(len(labels)), hours, color="#0284C7")
            ax.set_yticks(range(len(labels)))
            ax.set_yticklabels(labels)
            ax.set_xlabel("Часы")
            ax.invert_yaxis()
        fig.canvas.draw_idle()  # type: ignore[attr-defined]

    def _draw_months(self) -> None:
        fig = self._clear_fig(self.tab_months)
        if fig is None:
            return
        data = self.service.cases_by_month(12)
        ax = fig.add_subplot(111)
        labels = [d[0] for d in data]
        values = [d[1] for d in data]
        ax.plot(labels, values, marker="o", color="#4F46E5", linewidth=2)
        ax.set_xlabel("Месяц")
        ax.set_ylabel("Возбуждено дел")
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis="x", rotation=45)
        fig.canvas.draw_idle()  # type: ignore[attr-defined]
