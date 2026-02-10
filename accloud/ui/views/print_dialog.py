import json
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ...api import get_gcode_info, list_printers, send_print_order
from ...client import CloudClient
from ...models import FileItem
from ...image_cache import fetch_image_bytes
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


def _fmt_seconds_hms(value: Any) -> str:
    try:
        if value is None:
            return "-"
        total = int(float(value))
    except (TypeError, ValueError):
        return "-"
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h}h{m:02d}m{s:02d}s"


def _fmt_float(value: Any, decimals: int = 2) -> str:
    try:
        if value is None:
            return "-"
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return "-"


class PrintDialog(QDialog):
    def __init__(
        self,
        client: CloudClient,
        item: FileItem,
        parent=None,
        on_print_success: Optional[Callable[[str], None]] = None,
    ) -> None:
        super().__init__(parent)
        self._client = client
        self._item = item
        self._runner = TaskRunner()
        self._printers: Dict[str, Dict[str, Any]] = {}
        self._on_print_success = on_print_success

        self.setWindowTitle("Print")
        self.setModal(True)
        self.setFixedSize(520, 680)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Print")
        title.setStyleSheet("font-weight: 600; font-size: 16px;")
        header.addWidget(title)
        header.addStretch(1)
        root.addLayout(header)

        task_row = QHBoxLayout()
        task_label = QLabel("Task name:")
        self.task_value = QLabel(self._item.name.replace(".pwmb", ""))
        self.task_value.setStyleSheet("font-weight: 600;")
        task_row.addWidget(task_label)
        task_row.addWidget(self.task_value)
        task_row.addStretch(1)
        root.addLayout(task_row)

        self.preview = QLabel("No preview")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setFixedSize(460, 260)
        self.preview.setStyleSheet("background: #0f3f47; color: #bfe4e9; border-radius: 10px;")
        root.addWidget(self.preview, alignment=Qt.AlignCenter)

        info_bar = QHBoxLayout()
        self.info_printer = QLabel("Printer: -")
        self.info_time = QLabel("Time: -")
        self.info_resin = QLabel("Resin: -")
        info_bar.addWidget(self.info_printer)
        info_bar.addWidget(self.info_time)
        info_bar.addWidget(self.info_resin)
        info_bar.addStretch(1)
        root.addLayout(info_bar)

        self.printer_card = QFrame()
        self.printer_card.setStyleSheet(
            "background: #f6f7f9; border-radius: 10px; border: 1px solid #e6e6e6;"
        )
        card_layout = QHBoxLayout(self.printer_card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(8)
        cloud = QLabel("Cloud")
        cloud.setStyleSheet("color: #1d6fd6; font-weight: 600;")
        card_layout.addWidget(cloud)
        labels = QVBoxLayout()
        self.printer_name = QLabel("-")
        self.printer_name.setStyleSheet("font-weight: 600;")
        self.printer_sub = QLabel("-")
        self.printer_sub.setStyleSheet("color: #666666;")
        labels.addWidget(self.printer_name)
        labels.addWidget(self.printer_sub)
        card_layout.addLayout(labels, 1)
        self.printer_combo = QComboBox()
        self.printer_combo.currentIndexChanged.connect(self._on_printer_changed)
        card_layout.addWidget(self.printer_combo)
        root.addWidget(self.printer_card)

        footer = QHBoxLayout()
        footer.addStretch(1)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setToolTip("Cancel printing")
        self.cancel_btn.clicked.connect(self.reject)
        self.start_btn = QPushButton("Start Printing")
        self.start_btn.setStyleSheet("background: #1d6fd6; color: #ffffff;")
        self.start_btn.setToolTip("Start printing this file")
        self.start_btn.clicked.connect(self._start_print)
        footer.addWidget(self.cancel_btn)
        footer.addWidget(self.start_btn)
        root.addLayout(footer)

        self._load_printers()
        self._load_gcode_info()
        self._load_preview()

    def _load_printers(self) -> None:
        def work():
            return list_printers(self._client, params={"page": 1, "limit": 50})

        def done(data):
            items = data if isinstance(data, list) else data.get("list") or data.get("rows") or data.get("data") or []
            self._printers = {}
            self.printer_combo.blockSignals(True)
            self.printer_combo.clear()
            for item in items:
                pid = str(item.get("id") or item.get("printer_id") or item.get("device_id") or "")
                name = item.get("printer_name") or item.get("machine_name") or item.get("name") or pid
                if pid:
                    item["_pid"] = pid
                    self._printers[name] = item
                    self.printer_combo.addItem(name)
            self.printer_combo.blockSignals(False)
            if self.printer_combo.count() > 0:
                self.printer_combo.setCurrentIndex(0)
                self._on_printer_changed(0)

        self._runner.run(work, on_result=done)

    def _on_printer_changed(self, _index: int) -> None:
        name = self.printer_combo.currentText() or "-"
        self.printer_name.setText(name)
        self.printer_sub.setText(name)
        self.info_printer.setText(f"Printer: {name}")

    def _load_gcode_info(self) -> None:
        if not self._item.gcode_id:
            return

        def work():
            return get_gcode_info(self._client, self._item.gcode_id)

        def done(info):
            slice_param = _parse_json(info.get("slice_param"))
            estimate = slice_param.get("estimate")
            resin = slice_param.get("supplies_usage")
            self.info_time.setText(f"Time: {_fmt_seconds_hms(estimate)}")
            self.info_resin.setText(f"Resin: {_fmt_float(resin, 3)} ml")

        self._runner.run(work, on_result=done)

    def _load_preview(self) -> None:
        if not self._item.thumbnail:
            return

        def work():
            return fetch_image_bytes(self._item.thumbnail, timeout=20.0)

        def done(data: bytes):
            if not data:
                return
            image = QImage()
            image.loadFromData(data)
            if image.isNull():
                return
            pix = QPixmap.fromImage(image)
            self.preview.setPixmap(pix.scaled(420, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        self._runner.run(work, on_result=done)

    def _start_print(self) -> None:
        name = self.printer_combo.currentText()
        entry = self._printers.get(name)
        pid = entry.get("_pid") if entry else None
        if not pid:
            QMessageBox.information(self, "Print", "Select a printer.")
            return
        device_status = entry.get("device_status") if entry else None
        reason = entry.get("reason")
        if device_status in (0, "0", 2, "2") or reason == "offline":
            QMessageBox.information(self, "Print", "Imprimante hors ligne. Impossible de lancer une impression.")
            return

        project_id = "0"
        order_id = "1"
        is_delete = "0"
        project_type = "1"
        filetype = "0"
        template_id = "-2074360784"
        matrix = ""

        def work():
            return send_print_order(
                self._client,
                file_id=str(self._item.id),
                printer_id=str(pid),
                project_id=project_id,
                order_id=order_id,
                is_delete_file=is_delete,
                data_payload={
                    "file_id": str(self._item.id),
                    "matrix": matrix,
                    "filetype": int(filetype),
                    "project_type": int(project_type),
                    "template_id": int(template_id),
                },
            )

        def done(_data):
            if self._on_print_success:
                self._on_print_success(str(pid))
            self.accept()

        def err(exc: Exception) -> None:
            QMessageBox.information(self, "Print", f"Print failed: {exc}")

        self._runner.run(work, on_result=done, on_error=err)
