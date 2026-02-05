import json
from datetime import datetime
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...api import get_projects
from ...client import CloudClient
from ..threads import TaskRunner


def _parse_json(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


def _fmt_ts(ts: Any) -> str:
    try:
        if ts is None:
            return "-"
        ts_int = int(float(ts))
        if ts_int > 10_000_000_000:
            ts_int = int(ts_int / 1000)
        return datetime.fromtimestamp(ts_int).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return "-"


class TaskHistoryTab(QWidget):
    def __init__(self, status_cb=None, parent=None) -> None:
        super().__init__(parent)
        self._status = status_cb or (lambda _msg: None)
        self._client: Optional[CloudClient] = None
        self._runner = TaskRunner()
        self._printer_id: Optional[str] = None

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        top = QHBoxLayout()
        top.addWidget(QLabel("Task History"))
        top.addStretch(1)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.setToolTip("Refresh task history")
        self.refresh_btn.clicked.connect(self.refresh)
        top.addWidget(self.refresh_btn)
        root.addLayout(top)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Task ID", "File", "Status", "Progress", "Finished At"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, 1)

    def set_client(self, client: CloudClient, printer_id: Optional[str] = None) -> None:
        self._client = client
        self._printer_id = printer_id
        self.refresh()

    def set_printer_id(self, printer_id: str) -> None:
        self._printer_id = printer_id
        self.refresh()

    def refresh(self) -> None:
        if not self._client or not self._printer_id:
            self._status("No printer selected.")
            return
        self._status("Loading task history...")
        self._runner.run(self._load_tasks, on_result=self._apply_tasks, on_error=self._on_error)

    def _load_tasks(self):
        # print_status=2 is assumed to be completed tasks (may vary by API).
        return get_projects(self._client, self._printer_id, print_status=2, page=1, limit=50)

    def _apply_tasks(self, data: Dict[str, Any]) -> None:
        if isinstance(data, list):
            items = data
        else:
            items = data.get("list") or data.get("rows") or data.get("data") or []
        self.table.setRowCount(0)
        for row, item in enumerate(items):
            settings = _parse_json(item.get("settings"))
            task_id = item.get("taskid") or item.get("task_id") or item.get("id") or "-"
            filename = settings.get("filename") or item.get("gcode_name") or item.get("name") or "-"
            status = item.get("state") or settings.get("state") or item.get("print_status") or "-"
            progress = item.get("progress") or settings.get("progress") or "-"
            finished = item.get("finish_time") or item.get("end_time") or item.get("last_update_time")

            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(task_id)))
            self.table.setItem(row, 1, QTableWidgetItem(str(filename)))
            self.table.setItem(row, 2, QTableWidgetItem(str(status)))
            self.table.setItem(row, 3, QTableWidgetItem(str(progress)))
            self.table.setItem(row, 4, QTableWidgetItem(_fmt_ts(finished)))

        self._status(f"Loaded {len(items)} task(s).")

    def _on_error(self, exc: Exception) -> None:
        self._status(f"Error: {exc}")
