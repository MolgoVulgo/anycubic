import os

from PySide6.QtCore import QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QLabel, QPlainTextEdit, QVBoxLayout, QWidget


class LogTailWidget(QWidget):
    def __init__(self, path: str, parent=None) -> None:
        super().__init__(parent)
        self.path = path
        self._offset = 0

        layout = QVBoxLayout(self)
        self.status = QLabel(f"Log file: {self.path}")
        self.box = QPlainTextEdit()
        self.box.setReadOnly(True)
        layout.addWidget(self.status)
        layout.addWidget(self.box)

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._poll)
        self.timer.start()

    def _poll(self) -> None:
        if not os.path.exists(self.path):
            self.status.setText(f"Log file not found: {self.path}")
            return
        try:
            with open(self.path, "r", encoding="utf-8", errors="ignore") as handle:
                handle.seek(self._offset)
                data = handle.read()
                self._offset = handle.tell()
            if data:
                self.box.moveCursor(QTextCursor.End)
                self.box.insertPlainText(data)
                self.box.moveCursor(QTextCursor.End)
        except Exception as exc:
            self.status.setText(f"Log read error: {exc}")


class MqttTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        log_path = os.path.join(os.getcwd(), "accloud_mqtt.log")
        layout.addWidget(LogTailWidget(log_path, self))
