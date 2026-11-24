"""QSS-стили (светлая тема)."""

LIGHT_QSS = """
QWidget {
    background-color: #F7F8FA;
    color: #0F172A;
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', 'Helvetica Neue', sans-serif;
    font-size: 13px;
}
QLabel#h1 {
    font-size: 22px;
    font-weight: 600;
    color: #0F172A;
}
QLabel#caption {
    color: #475569;
    font-size: 12px;
}
QLabel#hint {
    color: #94A3B8;
    font-size: 11px;
}
QLabel#danger {
    color: #DC2626;
    font-size: 12px;
}
QGroupBox {
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    margin-top: 12px;
    padding: 16px 12px 12px 12px;
    background-color: #FFFFFF;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #475569;
    font-size: 12px;
}
QLineEdit {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 22px;
}
QLineEdit:focus {
    border: 1px solid #4F46E5;
}
QPushButton {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 8px 16px;
    min-height: 24px;
}
QPushButton:hover {
    background-color: #F1F3F5;
}
QPushButton#primary {
    background-color: #4F46E5;
    color: #FFFFFF;
    border: none;
}
QPushButton#primary:hover {
    background-color: #4338CA;
}
QPushButton#primary:disabled {
    background-color: #A5B4FC;
}

QPushButton#linkButton {
    background: transparent;
    border: none;
    color: #4F46E5;
    text-decoration: underline;
    font-size: 12px;
    padding: 2px 4px;
}
QPushButton#linkButton:hover {
    color: #4338CA;
}
QPushButton#togglePassword {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 0;
}
QPushButton#togglePassword:hover {
    background-color: #F1F3F5;
    border-color: #E5E7EB;
}
QPushButton#togglePassword:checked {
    background-color: #EEF2FF;
    border-color: #E5E7EB;
}

"""

DARK_QSS = """
QWidget {
    background-color: #0B0F14;
    color: #E6EDF3;
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', 'Helvetica Neue', sans-serif;
    font-size: 13px;
}
QLabel#h1 {
    font-size: 22px;
    font-weight: 600;
    color: #E6EDF3;
}
QLabel#caption {
    color: #9BA7B4;
    font-size: 12px;
}
QLabel#hint {
    color: #6B7785;
    font-size: 11px;
}
QLabel#danger {
    color: #F87171;
    font-size: 12px;
}
QGroupBox {
    border: 1px solid #1F2933;
    border-radius: 12px;
    margin-top: 12px;
    padding: 16px 12px 12px 12px;
    background-color: #131920;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #9BA7B4;
    font-size: 12px;
}
QLineEdit {
    background-color: #131920;
    border: 1px solid #2D3748;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 22px;
    color: #E6EDF3;
}
QLineEdit:focus {
    border: 1px solid #6366F1;
}
QTextEdit {
    background-color: #131920;
    border: 1px solid #2D3748;
    border-radius: 6px;
    color: #E6EDF3;
}
QPushButton {
    background-color: #131920;
    border: 1px solid #2D3748;
    border-radius: 8px;
    padding: 8px 16px;
    min-height: 24px;
    color: #E6EDF3;
}
QPushButton:hover {
    background-color: #1B222C;
}
QPushButton#primary {
    background-color: #6366F1;
    color: #FFFFFF;
    border: none;
}
QPushButton#primary:hover {
    background-color: #818CF8;
}
QPushButton#primary:disabled {
    background-color: #3730A3;
}
QPushButton#linkButton {
    background: transparent;
    border: none;
    color: #818CF8;
    text-decoration: underline;
    font-size: 12px;
    padding: 2px 4px;
}
QPushButton#linkButton:hover {
    color: #A5B4FC;
}
QPushButton#togglePassword {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 0;
}
QPushButton#togglePassword:hover {
    background-color: #1B222C;
    border-color: #2D3748;
}
QTableWidget {
    background-color: #131920;
    border: 1px solid #1F2933;
    gridline-color: #1F2933;
    color: #E6EDF3;
    alternate-background-color: #0F151C;
}
QHeaderView::section {
    background-color: #1B222C;
    border: none;
    padding: 6px;
    color: #9BA7B4;
    font-weight: 600;
}
QListView {
    background-color: #0B0F14;
    border: none;
}
QTabWidget::pane {
    background-color: #131920;
    border: 1px solid #1F2933;
    border-radius: 8px;
}
QTabBar::tab {
    background-color: #0B0F14;
    color: #9BA7B4;
    padding: 8px 16px;
    border: none;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected {
    color: #E6EDF3;
    border-bottom: 2px solid #6366F1;
}
QComboBox {
    background-color: #131920;
    border: 1px solid #2D3748;
    border-radius: 6px;
    padding: 6px 10px;
    color: #E6EDF3;
}
QComboBox QAbstractItemView {
    background-color: #131920;
    color: #E6EDF3;
    selection-background-color: #1E1B4B;
}
QCheckBox, QRadioButton {
    color: #E6EDF3;
}
QScrollBar:vertical {
    background: #0B0F14;
    width: 12px;
}
QScrollBar::handle:vertical {
    background: #2D3748;
    border-radius: 6px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #475569;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QMenuBar {
    background-color: #0B0F14;
    color: #E6EDF3;
}
QMenu {
    background-color: #131920;
    color: #E6EDF3;
    border: 1px solid #1F2933;
}
QMenu::item:selected {
    background-color: #1E1B4B;
}
QToolTip {
    background-color: #1B222C;
    color: #E6EDF3;
    border: 1px solid #2D3748;
    padding: 4px;
}
QMessageBox {
    background-color: #131920;
}
QDialog {
    background-color: #0B0F14;
}
QStatusBar {
    background-color: #0B0F14;
    color: #9BA7B4;
}
"""
