import json
import os
from collections import OrderedDict
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from PySide6.QtCore import Qt, QTimer
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
    QSpacerItem,
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
    return f"{h:02d}:{m:02d}"


class CardFrame(QFrame):
    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(
            "#card { background: #ffffff; border-radius: 10px; border: 1px solid #e6e6e6; }"
        )
        self._title = QLabel(title, self)
        self._title.setStyleSheet("font-weight: 600;")
        self._divider = QFrame(self)
        self._divider.setFixedHeight(2)
        self._divider.setStyleSheet("background: #e6e6e6;")
        self.setMinimumHeight(320)
        self._position_header()

    def _position_header(self) -> None:
        self._title.move(12, 8)
        width = max(self.width() - 24, 10)
        self._divider.setGeometry(12, 30, width, 2)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_header()


class PrinterTab(QWidget):
    def __init__(self, status_cb: Optional[Callable[[str], None]] = None, parent=None) -> None:
        super().__init__(parent)
        self._status = status_cb or (lambda _msg: None)
        self._client: Optional[CloudClient] = None
        self._runner = TaskRunner()
        self._printers: Dict[str, Dict[str, Any]] = {}
        self._thumbs_enabled = os.getenv("ACCLOUD_DISABLE_THUMBS", "0") not in ("1", "true", "TRUE")
        self._on_printer_id_changed: Optional[Callable[[str], None]] = None
        self._on_print_completed: Optional[Callable[[str], None]] = None
        self._image_cache: "OrderedDict[str, QPixmap]" = OrderedDict()
        self._image_inflight = set()
        self._image_cache_max = 64
        self._poll_interval_idle_ms = 15000
        self._poll_interval_active_ms = 5000
        self._has_active_print = False
        self._was_active_print = False
        self._job_is_paused = False
        self._elapsed_seconds: Optional[int] = None
        self._remaining_seconds: Optional[int] = None
        self._poll_inflight = False
        self._poll_pending = 0
        self._poll_timer = QTimer(self)
        self._poll_timer.setSingleShot(True)
        self._poll_timer.timeout.connect(self._poll_printer)
        self._time_timer = QTimer(self)
        self._time_timer.setInterval(1000)
        self._time_timer.timeout.connect(self._tick_time)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)
        self.setStyleSheet("QLabel { color: #111111; padding: 0px; margin: 0px; }")

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
        self._schedule_poll(1500)

    def set_printer_id_callback(self, callback: Callable[[str], None]) -> None:
        self._on_printer_id_changed = callback

    def set_print_completed_callback(self, callback: Callable[[str], None]) -> None:
        self._on_print_completed = callback

    def notify_print_started(self, printer_id: Optional[str] = None) -> None:
        if not self._client:
            return
        self._has_active_print = True
        self._was_active_print = True
        self._job_is_paused = False
        self._ensure_time_timer()
        if printer_id:
            for idx in range(self.printer_combo.count()):
                if self.printer_combo.itemData(idx) == printer_id:
                    self.printer_combo.setCurrentIndex(idx)
                    self._load_printer_details()
                    self._schedule_poll(1000)
                    return
        self.refresh()
        self._schedule_poll(1000)

    def refresh(self) -> None:
        if not self._client:
            self._status("No session loaded.")
            return
        self._status("Loading printers...")
        self._runner.run(self._load_printers, on_result=self._apply_printers, on_error=self._on_error)
        self._schedule_poll(2000)

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

    def _schedule_poll(self, delay_ms: int) -> None:
        if not self._client:
            return
        self._poll_timer.stop()
        self._poll_timer.start(max(500, int(delay_ms)))

    def _poll_printer(self) -> None:
        if not self._client:
            return
        pid = self._selected_printer_id()
        if not pid:
            self._schedule_poll(self._poll_interval_idle_ms)
            return
        if self._poll_inflight:
            next_delay = self._poll_interval_active_ms if self._has_active_print else self._poll_interval_idle_ms
            self._schedule_poll(next_delay)
            return
        self._poll_inflight = True
        self._poll_pending = 2

        def _finish() -> None:
            self._poll_pending = max(self._poll_pending - 1, 0)
            if self._poll_pending == 0:
                self._poll_inflight = False
                next_delay = self._poll_interval_active_ms if self._has_active_print else self._poll_interval_idle_ms
                self._schedule_poll(next_delay)

        self._runner.run(
            lambda: get_printer_info_v2(self._client, pid),
            on_result=self._apply_printer_info,
            on_error=self._on_error,
            on_finished=_finish,
        )
        self._runner.run(
            lambda: get_projects(self._client, pid, print_status=1, page=1, limit=1),
            on_result=self._apply_projects,
            on_error=self._on_error,
            on_finished=_finish,
        )

    def _selected_printer_id(self) -> Optional[str]:
        if self.printer_combo.count() == 0:
            return None
        return self.printer_combo.currentData()

    def _build_left(self) -> None:
        layout = QGridLayout(self.left)
        layout.setContentsMargins(12, 40, 12, 12)
        layout.setVerticalSpacing(1)

        self.left_name = QLabel("-")
        self.left_status = QLabel("-")
        self.left_type = QLabel("-")
        self.left_device = QLabel("-")
        self.left_image = QLabel()
        self.left_image.setFixedSize(200, 200)
        self.left_image.setStyleSheet("background: #f2f2f2; border: 1px solid #dddddd; margin-top: 20px;")
        self.left_image.setAlignment(Qt.AlignCenter)

        for label in (self.left_name, self.left_status, self.left_type, self.left_device):
            label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        name_lbl = QLabel("Name:")
        status_lbl = QLabel("Status:")
        type_lbl = QLabel("Printer Type:")
        device_lbl = QLabel("Device CN:")
        for label in (name_lbl, status_lbl, type_lbl, device_lbl):
            label.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        layout.addWidget(name_lbl, 0, 0, alignment=Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self.left_name, 0, 1, alignment=Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(status_lbl, 1, 0, alignment=Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self.left_status, 1, 1, alignment=Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(type_lbl, 2, 0, alignment=Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self.left_type, 2, 1, alignment=Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(device_lbl, 3, 0, alignment=Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self.left_device, 3, 1, alignment=Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self.left_image, 4, 0, 1, 2, alignment=Qt.AlignTop | Qt.AlignHCenter)
        layout.setRowStretch(4, 1)

    def _build_center(self) -> None:
        layout = QVBoxLayout(self.center)
        layout.setContentsMargins(12, 40, 12, 12)
        layout.setSpacing(1)

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
        self.progress_bar.setStyleSheet(
            "QProgressBar { border: 1px solid #d5d5d5; border-radius: 6px; text-align: center; height: 14px; }"
            "QProgressBar::chunk { background: #2f80ed; border-radius: 6px; }"
        )
        layout.addSpacing(20)
        layout.addWidget(self.progress_bar)

        self.preview = QLabel()
        self.preview.setFixedSize(220, 220)
        self.preview.setStyleSheet(
            "background: #f2f2f2; border: 1px solid #dddddd; margin-top: 20px; margin-bottom: 20px;"
        )
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
        layout.addStretch(1)

    def _build_right(self) -> None:
        layout = QGridLayout(self.right)
        layout.setContentsMargins(12, 40, 12, 12)
        layout.setVerticalSpacing(1)

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
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding), 5, 0, 1, 2)

    def _apply_printer_info(self, info: Dict[str, Any]) -> None:
        name = info.get("printer_name") or info.get("machine_name") or info.get("name") or "-"
        material_type = self._material_type_for_printer(info)
        status = self._derive_online_status(info)
        device = info.get("key") or info.get("device_cn") or "-"
        self.left_name.setText(str(name))
        self.left_type.setText(str(material_type))
        self.left_status.setText(str(status))
        if status == "Online":
            self.left_status.setStyleSheet("color: #2e7d32; font-weight: 600;")
        elif status == "Offline":
            self.left_status.setStyleSheet("color: #c62828; font-weight: 600;")
        else:
            self.left_status.setStyleSheet("")
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
        if isinstance(data, list):
            items = data
        else:
            items = data.get("list") or data.get("rows") or data.get("data") or []
        if not items:
            was_active = self._was_active_print
            self._has_active_print = False
            self._was_active_print = False
            self._job_is_paused = False
            self._elapsed_seconds = None
            self._remaining_seconds = None
            self._ensure_time_timer()
            self._clear_job()
            if was_active and self._on_print_completed:
                pid = self._selected_printer_id()
                if pid:
                    self._on_print_completed(pid)
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
        self.metrics_size.setText(self._fmt_size(slice_param, settings))

        img_url = job.get("img") or job.get("image_id")
        if self._thumbs_enabled and img_url:
            self._load_preview(img_url)

        job_status = self._derive_job_status(job, settings)
        self._has_active_print = job_status in ("Busy", "Paused")
        if self._has_active_print:
            self._was_active_print = True
        self._job_is_paused = job_status == "Paused"
        self._sync_time_counters(job, settings)
        self._ensure_time_timer()

    def _fmt_resin(self, job: Dict[str, Any], settings: Dict[str, Any], slice_param: Dict[str, Any]) -> str:
        val = settings.get("supplies_usage")
        if val is None:
            val = slice_param.get("supplies_usage")
        if val is None:
            val = job.get("material")
        return f"{_fmt_float(val, 2)}ml" if val is not None else "-"

    def _fmt_size(self, slice_param: Dict[str, Any], settings: Dict[str, Any]) -> str:
        try:
            x = float(slice_param.get("size_x") or 0)
            y = float(slice_param.get("size_y") or 0)
            z = float(slice_param.get("size_z") or 0)
        except (TypeError, ValueError):
            return "-"
        if z == 0:
            try:
                layers = int(slice_param.get("layers") or settings.get("total_layers") or 0)
                zthick = float(slice_param.get("zthick") or settings.get("z_thick") or 0)
                if layers and zthick:
                    z = layers * zthick
            except (TypeError, ValueError):
                z = 0
        if x == 0 and y == 0:
            if z == 0:
                return "-"
            cm = z / 10.0
            return f"H: {_fmt_float(z, 2)} mm ({_fmt_float(cm, 2)} cm)"
        if z == 0:
            return f"{_fmt_float(x, 2)} x {_fmt_float(y, 2)} mm"
        cm = z / 10.0
        return f"{_fmt_float(x, 2)} x {_fmt_float(y, 2)} x {_fmt_float(z, 2)} mm ({_fmt_float(cm, 2)} cm)"

    def _fmt_elapsed(self, job: Dict[str, Any]) -> str:
        elapsed = self._calc_elapsed_seconds(job)
        return _fmt_seconds_hms(elapsed) if elapsed is not None else "-"

    def _fmt_remaining(self, job: Dict[str, Any], settings: Dict[str, Any]) -> str:
        remain = self._calc_remaining_seconds(job, settings)
        return _fmt_seconds_hms(remain) if remain is not None else "-"

    def _calc_elapsed_seconds(self, job: Dict[str, Any]) -> Optional[int]:
        start = job.get("start_time")
        last = job.get("last_update_time")
        if start and last:
            try:
                start_ts = int(float(start))
                last_ts = int(float(last))
                if last_ts > 10_000_000_000:
                    last_ts = int(last_ts / 1000)
                return max(last_ts - start_ts, 0)
            except (TypeError, ValueError):
                return None
        return None

    def _calc_remaining_seconds(self, job: Dict[str, Any], settings: Dict[str, Any]) -> Optional[int]:
        remain = settings.get("remain_time")
        if remain is None:
            remain = job.get("remain_time")
        if remain is None:
            return None
        try:
            minutes = float(remain)
            return max(int(minutes * 60), 0)
        except (TypeError, ValueError):
            return None

    def _sync_time_counters(self, job: Dict[str, Any], settings: Dict[str, Any]) -> None:
        cloud_elapsed = self._calc_elapsed_seconds(job)
        cloud_remaining = self._calc_remaining_seconds(job, settings)
        self._elapsed_seconds = self._sync_counter(self._elapsed_seconds, cloud_elapsed)
        self._remaining_seconds = self._sync_counter(self._remaining_seconds, cloud_remaining)
        self._update_time_labels()

    def _sync_counter(self, local: Optional[int], cloud: Optional[int]) -> Optional[int]:
        if cloud is None:
            return local
        if local is None:
            return cloud
        if abs(local - cloud) > 5:
            return cloud
        return local

    def _ensure_time_timer(self) -> None:
        if self._has_active_print:
            if not self._time_timer.isActive():
                self._time_timer.start()
        else:
            if self._time_timer.isActive():
                self._time_timer.stop()

    def _tick_time(self) -> None:
        if not self._has_active_print or self._job_is_paused:
            return
        if self._elapsed_seconds is not None:
            self._elapsed_seconds += 1
        if self._remaining_seconds is not None:
            self._remaining_seconds = max(0, self._remaining_seconds - 1)
        self._update_time_labels()

    def _update_time_labels(self) -> None:
        if self._elapsed_seconds is not None:
            self.metrics_elapsed.setText(_fmt_seconds_hms(self._elapsed_seconds))
        else:
            self.metrics_elapsed.setText("-")
        if self._remaining_seconds is not None:
            self.metrics_remaining.setText(_fmt_seconds_hms(self._remaining_seconds))
        else:
            self.metrics_remaining.setText("-")

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
        self._elapsed_seconds = None
        self._remaining_seconds = None
        self._update_time_labels()
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

    def _derive_online_status(self, info: Dict[str, Any]) -> str:
        device_status = info.get("device_status")
        if device_status in (0, "0", 2, "2"):
            return "Offline"
        if device_status in (1, "1"):
            return "Online"
        return "-"

    def _material_type_for_printer(self, info: Dict[str, Any]) -> str:
        material_type = info.get("material_type")
        if not material_type and isinstance(info.get("base"), dict):
            material_type = info["base"].get("material_type")
        if not material_type:
            pid = self._selected_printer_id()
            if pid and pid in self._printers:
                material_type = self._printers[pid].get("material_type")
        return material_type or "-"

    def _derive_job_status(self, job: Dict[str, Any], settings: Dict[str, Any]) -> Optional[str]:
        state = settings.get("state") or job.get("state")
        pause = job.get("pause") or settings.get("pause")
        print_status = job.get("print_status") or job.get("status")
        if pause in (1, "1") or state == "paused":
            return "Paused"
        if state == "printing" or print_status in (1, "1"):
            return "Busy"
        if state in ("finished", "done", "complete", "completed"):
            return None
        return None

    def _pause_not_implemented(self) -> None:
        QMessageBox.information(self, "Pause", "Pause not implemented in Qt UI yet.")

    def _stop_not_implemented(self) -> None:
        QMessageBox.information(self, "Stop", "Stop not implemented in Qt UI yet.")

    def _on_error(self, exc: Exception) -> None:
        self._status(f"Error: {exc}")

    def _card(self, title: str) -> QFrame:
        return CardFrame(title)
