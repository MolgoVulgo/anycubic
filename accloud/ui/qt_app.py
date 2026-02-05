import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QTabWidget, QPushButton, QToolButton

from ..client import CloudClient
from ..session_store import DEFAULT_SESSION_PATH, load_session, load_session_from_har, save_session
from .state import AppState
from .views.files_tab import FilesTab
from .views.log_tab import LogTab
from .views.printer_tab import PrinterTab
from .views.task_history_tab import TaskHistoryTab


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Anycubic Cloud (Qt)")
        self.resize(1200, 800)

        self.state = AppState()

        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)

        self.files_tab = FilesTab(status_cb=self._set_status)
        self.printer_tab = PrinterTab(status_cb=self._set_status)
        self.task_history_tab = TaskHistoryTab(status_cb=self._set_status)
        self.log_tab = LogTab()

        self.tabs.addTab(self.files_tab, "Files")
        self.tabs.addTab(self.printer_tab, "Printer")
        self.tabs.addTab(self.task_history_tab, "Task History")
        self.tabs.addTab(self.log_tab, "LOG")

        self._build_menu()
        self.statusBar().showMessage("Ready")
        self._auto_load_session()
        self._apply_pointer_cursors()
        self.printer_tab.set_printer_id_callback(self.task_history_tab.set_printer_id)

    def _apply_pointer_cursors(self) -> None:
        for btn in self.findChildren(QPushButton):
            btn.setCursor(Qt.PointingHandCursor)
        for btn in self.findChildren(QToolButton):
            btn.setCursor(Qt.PointingHandCursor)

    def _build_menu(self) -> None:
        menu = self.menuBar().addMenu("Session")
        act_session = QAction("Load session.json", self)
        act_session.setStatusTip("Load a session.json file")
        act_session.triggered.connect(self._load_session_dialog)
        menu.addAction(act_session)

        act_har = QAction("Import HAR", self)
        act_har.setStatusTip("Import a HAR file to create a session")
        act_har.triggered.connect(self._import_har_dialog)
        menu.addAction(act_har)

    def _load_session_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select session.json", filter="JSON files (*.json)")
        if not path:
            return
        self._init_client_from_session(path)

    def _import_har_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select HAR file", filter="HAR files (*.har)")
        if not path:
            return
        session = load_session_from_har(path)
        save_session(DEFAULT_SESSION_PATH, session["cookies"], session.get("tokens", {}))
        self._init_client_from_session(DEFAULT_SESSION_PATH)
        self._set_status(f"Imported HAR -> {DEFAULT_SESSION_PATH}")

    def _init_client_from_session(self, path: str) -> None:
        session = load_session(path)
        client = CloudClient(cookies=session["cookies"], tokens=session.get("tokens", {}))
        self.state.client = client
        self.state.session_path = path
        self.files_tab.set_client(client)
        self.printer_tab.set_client(client)
        self.task_history_tab.set_client(client)
        self._set_status(f"Session loaded: {path}")

    def _auto_load_session(self) -> None:
        if not os.path.exists(DEFAULT_SESSION_PATH):
            return
        try:
            self._init_client_from_session(DEFAULT_SESSION_PATH)
        except Exception as exc:
            self._set_status(f"Session auto-load failed: {exc}")
            msg = QMessageBox(self)
            msg.setWindowTitle("Session")
            msg.setText("Session auto-load failed. Import a HAR file?")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if msg.exec() == QMessageBox.StandardButton.Yes:
                self._import_har_dialog()

    def _set_status(self, text: str) -> None:
        self.statusBar().showMessage(text)

    def closeEvent(self, event) -> None:
        if self.state.client:
            try:
                self.state.client.close()
            except Exception:
                pass
        super().closeEvent(event)
