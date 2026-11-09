"""QSS-стили (светлая тема)."""

LIGHT_QSS = """
QWidget {
    background-color: #F7F8FA;
    color: #0F172A;
    font-family: 'Inter', 'Segoe UI', sans-serif;
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
"""