import json
import os
from collections import OrderedDict
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from ...api import get_printer_info_v2, get_projects, list_printers
from ...client import CloudClient
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


def _fmt_float(value: Any, decimals: int = 2) -> str:
    try:
        if value is None:
            return "-"
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return "-"


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
    return f"{h:02d}:{m:02d}:{s:02d}"


class PrinterTab(QWidget):
    def __init__(self, status_cb: Optional[Callable[[str], None]] = None, parent=None) -> None:
        super().__init__(parent)
        self._status = status_cb or (lambda _msg: None)
        self._client: Optional[CloudClient] = None
        self._runner = TaskRunner()
        self._printers: Dict[str, Dict[str, Any]] = {}
        self._thumbs_enabled = os.getenv("ACCLOUD_DISABLE_THUMBS", "0") not in ("1", "true", "TRUE")
        self._on_printer_id_changed: Optional[Callable[[str], None]] = None
        self._image_cache: "OrderedDict[str, QPixmap]" = OrderedDict()
        self._image_inflight = set()
        self._image_cache_max = 64

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)
        self.setStyleSheet("QLabel { color: #111111; }")

        top = QHBoxLayout()
        self.printer_combo = QComboBox()
        self.printer_combo.currentIndexChanged.connect(self._on_printer_changed)
        top.addWidget(QLabel("Printers"))
        top.addWidget(self.printer_combo, 1)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.setToolTip("Refresh printer list")
        self.refresh_btn.clicked.connect(self.refresh)
        top.addWidget(self.refresh_btn)
        root.addLayout(top)

        columns = QHBoxLayout()
        columns.setSpacing(12)

        self.left = self._card("Printer info")
        self.center = self._card("Job viewer")
        self.right = self._card("Job metrics")

        columns.addWidget(self.left, 1)
        columns.addWidget(self.center, 1)
        columns.addWidget(self.right, 1)
        root.addLayout(columns, 1)

        self._build_left()
        self._build_center()
        self._build_right()

    def set_client(self, client: CloudClient) -> None:
        self._client = client
        self.refresh()

    def set_printer_id_callback(self, callback: Callable[[str], None]) -> None:
        self._on_printer_id_changed = callback

    def refresh(self) -> None:
        if not self._client:
            self._status("No session loaded.")
            return
        self._status("Loading printers...")
        self._runner.run(self._load_printers, on_result=self._apply_printers, on_error=self._on_error)

    def _load_printers(self):
        return list_printers(self._client, params={"page": 1, "limit": 50})

    def _apply_printers(self, data: Dict[str, Any]) -> None:
        if isinstance(data, list):
            items = data
        else:
            items = data.get("list") or data.get("rows") or data.get("data") or []
        self._printers = {}
        self.printer_combo.blockSignals(True)
        self.printer_combo.clear()
        for item in items:
            pid = str(item.get("id") or item.get("printer_id") or item.get("device_id") or "")
            name = item.get("printer_name") or item.get("machine_name") or item.get("name") or pid
            if pid:
                self._printers[pid] = item
                self.printer_combo.addItem(name, pid)
        self.printer_combo.blockSignals(False)
        if self.printer_combo.count() > 0:
            self.printer_combo.setCurrentIndex(0)
            self._load_printer_details()
        self._status("Printers loaded.")
        self._focus_active_printer()

    def _focus_active_printer(self) -> None:
        if not self._client or self.printer_combo.count() == 0:
            return

        def work():
            for idx in range(self.printer_combo.count()):
                pid = self.printer_combo.itemData(idx)
                if not pid:
                    continue
                data = get_projects(self._client, pid, print_status=1, page=1, limit=1)
                items = data if isinstance(data, list) else data.get("list") or data.get("rows") or data.get("data") or []
                if items:
                    return pid
            return None

        def done(pid):
            if not pid:
                return
            for idx in range(self.printer_combo.count()):
                if self.printer_combo.itemData(idx) == pid:
                    self.printer_combo.setCurrentIndex(idx)
                    break

        self._runner.run(work, on_result=done, on_error=self._on_error)

    def _on_printer_changed(self, _index: int) -> None:
        self._load_printer_details()

    def _load_printer_details(self) -> None:
        pid = self._selected_printer_id()
        if not pid or not self._client:
            return

        self._status("Loading printer status...")
        self._runner.run(
            lambda: get_printer_info_v2(self._client, pid),
            on_result=self._apply_printer_info,
            on_error=self._on_error,
        )
        self._runner.run(
            lambda: get_projects(self._client, pid, print_status=1, page=1, limit=1),
            on_result=self._apply_projects,
            on_error=self._on_error,
        )
        if self._on_printer_id_changed:
            self._on_printer_id_changed(pid)

    def _selected_printer_id(self) -> Optional[str]:
        if self.printer_combo.count() == 0:
            return None
        return self.printer_combo.currentData()

    def _build_left(self) -> None:
        layout = QGridLayout(self.left)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setVerticalSpacing(2)

        self.left_name = QLabel("-")
        self.left_status = QLabel("-")
        self.left_type = QLabel("-")
        self.left_device = QLabel("-")
        self.left_image = QLabel()
        self.left_image.setFixedSize(200, 200)
        self.left_image.setStyleSheet("background: #f2f2f2; border: 1px solid #dddddd;")
        self.left_image.setAlignment(Qt.AlignCenter)

        layout.addWidget(QLabel("Name:"), 0, 0)
        layout.addWidget(self.left_name, 0, 1)
        layout.addWidget(QLabel("Status:"), 1, 0)
        layout.addWidget(self.left_status, 1, 1)
        layout.addWidget(QLabel("Printer Type:"), 2, 0)
        layout.addWidget(self.left_type, 2, 1)
        layout.addWidget(QLabel("Device CN:"), 3, 0)
        layout.addWidget(self.left_device, 3, 1)
        layout.addWidget(self.left_image, 4, 0, 1, 2)

    def _build_center(self) -> None:
        layout = QVBoxLayout(self.center)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(2)

        self.job_name = QLabel("-")
        self.job_name.setStyleSheet("font-weight: 600;")
        self.job_state = QLabel("-")
        self.job_progress = QLabel("-")
        self.job_layers = QLabel("-")

        layout.addWidget(self.job_name)
        layout.addWidget(self.job_state)
        layout.addWidget(self.job_progress)
        layout.addWidget(self.job_layers)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        self.preview = QLabel()
        self.preview.setFixedSize(220, 220)
        self.preview.setStyleSheet("background: #f2f2f2; border: 1px solid #dddddd;")
        self.preview.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.preview, alignment=Qt.AlignCenter)

        buttons = QHBoxLayout()
        self.pause_btn = QPushButton("Pause")
        self.stop_btn = QPushButton("Stop")
        self.pause_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.pause_btn.setToolTip("Pause current print")
        self.stop_btn.setToolTip("Stop current print")
        self.pause_btn.clicked.connect(self._pause_not_implemented)
        self.stop_btn.clicked.connect(self._stop_not_implemented)
        buttons.addWidget(self.pause_btn)
        buttons.addWidget(self.stop_btn)
        layout.addLayout(buttons)

    def _build_right(self) -> None:
        layout = QGridLayout(self.right)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setVerticalSpacing(2)

        self.metrics_elapsed = QLabel("-")
        self.metrics_remaining = QLabel("-")
        self.metrics_layers = QLabel("-")
        self.metrics_resin = QLabel("-")
        self.metrics_size = QLabel("-")

        layout.addWidget(QLabel("Elapsed Time:"), 0, 0)
        layout.addWidget(self.metrics_elapsed, 0, 1)
        layout.addWidget(QLabel("Remaining Time:"), 1, 0)
        layout.addWidget(self.metrics_remaining, 1, 1)
        layout.addWidget(QLabel("Layers:"), 2, 0)
        layout.addWidget(self.metrics_layers, 2, 1)
        layout.addWidget(QLabel("Estimated Resin:"), 3, 0)
        layout.addWidget(self.metrics_resin, 3, 1)
        layout.addWidget(QLabel("Model Size:"), 4, 0)
        layout.addWidget(self.metrics_size, 4, 1)

    def _apply_printer_info(self, info: Dict[str, Any]) -> None:
        if not self.isVisible():
            return
        name = info.get("printer_name") or info.get("machine_name") or info.get("name") or "-"
        machine = info.get("machine_name") or info.get("printer_type") or "-"
        status = self._derive_status(info)
        device = info.get("key") or info.get("device_cn") or "-"
        self.left_name.setText(str(name))
        self.left_type.setText(str(machine))
        self.left_status.setText(str(status))
        self.left_device.setText(str(device))
        img_url = (
            info.get("image_id")
            or info.get("img")
            or info.get("image")
            or info.get("thumbnail")
            or info.get("machine_img")
            or info.get("machine_image")
            or info.get("printer_img")
            or info.get("printer_image")
        )
        if self._thumbs_enabled and img_url:
            self._load_image(self.left_image, img_url, 180)
        else:
            self.left_image.clear()

    def _apply_projects(self, data: Dict[str, Any]) -> None:
        if not self.isVisible():
            return
        if isinstance(data, list):
            items = data
        else:
            items = data.get("list") or data.get("rows") or data.get("data") or []
        if not items:
            self._clear_job()
            return
        job = items[0]
        settings = _parse_json(job.get("settings"))
        slice_param = _parse_json(job.get("slice_param"))

        filename = settings.get("filename") or job.get("gcode_name") or job.get("name") or "-"
        progress = int(job.get("progress") or settings.get("progress") or 0)
        curr_layer = settings.get("curr_layer") or "-"
        total_layers = settings.get("total_layers") or slice_param.get("layers") or "-"
        state = settings.get("state") or job.get("state") or "-"

        self.job_name.setText(str(filename))
        self.job_state.setText(f"State: {state}")
        self.job_progress.setText(f"Progress: {progress}%")
        self.job_layers.setText(f"Layers: {curr_layer} / {total_layers}")
        self.progress_bar.setValue(progress)

        self.metrics_layers.setText(f"{curr_layer} / {total_layers}")
        self.metrics_resin.setText(self._fmt_resin(job, settings, slice_param))
        self.metrics_size.setText(self._fmt_size(slice_param))
        self.metrics_elapsed.setText(self._fmt_elapsed(job))
        self.metrics_remaining.setText(self._fmt_remaining(job, settings))

        img_url = job.get("img") or job.get("image_id")
        if self._thumbs_enabled and img_url:
            self._load_preview(img_url)

    def _fmt_resin(self, job: Dict[str, Any], settings: Dict[str, Any], slice_param: Dict[str, Any]) -> str:
        val = settings.get("supplies_usage")
        if val is None:
            val = slice_param.get("supplies_usage")
        if val is None:
            val = job.get("material")
        return f"{_fmt_float(val, 2)}ml" if val is not None else "-"

    def _fmt_size(self, slice_param: Dict[str, Any]) -> str:
        try:
            x = float(slice_param.get("size_x") or 0)
            y = float(slice_param.get("size_y") or 0)
            z = float(slice_param.get("size_z") or 0)
        except (TypeError, ValueError):
            return "-"
        if x == 0 and y == 0:
            return "-"
        return f"{_fmt_float(x, 2)} x {_fmt_float(y, 2)} x {_fmt_float(z, 2)} mm"

    def _fmt_elapsed(self, job: Dict[str, Any]) -> str:
        start = job.get("start_time")
        last = job.get("last_update_time")
        if start and last:
            try:
                start_ts = int(float(start))
                last_ts = int(float(last))
                if last_ts > 10_000_000_000:
                    last_ts = int(last_ts / 1000)
                elapsed = max(last_ts - start_ts, 0)
                return _fmt_seconds_hms(elapsed)
            except (TypeError, ValueError):
                pass
        return "-"

    def _fmt_remaining(self, job: Dict[str, Any], settings: Dict[str, Any]) -> str:
        remain = settings.get("remain_time")
        if remain is None:
            remain = job.get("remain_time")
        if remain is None:
            return "-"
        return _fmt_seconds_hms(remain)

    def _load_preview(self, url: str) -> None:
        self._load_image(self.preview, url, 200)

    def _load_image(self, target: QLabel, url: str, size: int) -> None:
        if url in self._image_cache:
            pix = self._image_cache.pop(url)
            self._image_cache[url] = pix
            target.setPixmap(pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            return
        if url in self._image_inflight:
            return
        self._image_inflight.add(url)

        def work():
            return fetch_image_bytes(url, timeout=20.0)

        def done(data: bytes):
            self._image_inflight.discard(url)
            if not data:
                return
            image = QImage()
            image.loadFromData(data)
            if not image.isNull():
                pix = QPixmap.fromImage(image)
                self._image_cache[url] = pix
                while len(self._image_cache) > self._image_cache_max:
                    self._image_cache.popitem(last=False)
                target.setPixmap(pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        def failed(exc: Exception):
            self._image_inflight.discard(url)
            self._on_error(exc)

        self._runner.run(work, on_result=done, on_error=failed)

    def _clear_job(self) -> None:
        self.job_name.setText("-")
        self.job_state.setText("State: -")
        self.job_progress.setText("Progress: -")
        self.job_layers.setText("Layers: -")
        self.progress_bar.setValue(0)
        self.preview.clear()
        self.metrics_elapsed.setText("-")
        self.metrics_remaining.setText("-")
        self.metrics_layers.setText("-")
        self.metrics_resin.setText("-")
        self.metrics_size.setText("-")

    def _derive_status(self, info: Dict[str, Any]) -> str:
        connect_status = info.get("connect_status")
        device_status = info.get("device_status")
        print_status = info.get("print_status")
        pause = info.get("pause")
        state = info.get("state")
        if connect_status in (0, "0") or device_status in (0, "0"):
            return "Offline"
        if print_status in (1, "1") or state == "printing":
            return "Busy"
        if pause in (1, "1") or state == "paused":
            return "Paused"
        return "Idle"

    def _pause_not_implemented(self) -> None:
        QMessageBox.information(self, "Pause", "Pause not implemented in Qt UI yet.")

    def _stop_not_implemented(self) -> None:
        QMessageBox.information(self, "Stop", "Stop not implemented in Qt UI yet.")

    def _on_error(self, exc: Exception) -> None:
        self._status(f"Error: {exc}")

    def _card(self, title: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(
            "#card { background: #ffffff; border-radius: 10px; border: 1px solid #e6e6e6; }"
        )
        label = QLabel(title, card)
        label.setStyleSheet("font-weight: 600;")
        label.move(12, 8)
        card.setMinimumHeight(320)
        return card
