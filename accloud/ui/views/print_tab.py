from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PrintTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Print tab (Qt) - a porter selon besoin."))
