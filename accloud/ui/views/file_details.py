import json
from datetime import datetime
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ..threads import TaskRunner
from ...image_cache import fetch_image_bytes


def _format_ts(ts: Optional[int]) -> str:
    if not ts:
        return "-"
    if ts > 10_000_000_000:
        ts = int(ts / 1000)
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def _format_mb(num: Optional[int]) -> str:
    if not num:
        return "-"
    mb = num / (1024 ** 2)
    return f"{mb:.2f} MB"


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


class FileDetailsWindow(QDialog):
    def __init__(
        self,
        base_info: Dict[str, Any],
        gcode_info: Optional[Dict[str, Any]] = None,
        note: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("File Details")
        self.resize(940, 720)
        self._runner = TaskRunner()

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        card_a = self._card()
        card_b = self._card()
        root.addWidget(card_a)
        root.addWidget(card_b)

        self._build_card_a(card_a, base_info)
        self._build_card_b(card_b, gcode_info or {}, note)

    def _card(self) -> QFrame:
        card = QFrame(self)
        card.setObjectName("card")
        card.setStyleSheet(
            "#card { background: #ffffff; border-radius: 10px; border: 1px solid #e6e6e6; }"
        )
        return card

    def _build_card_a(self, card: QFrame, base_info: Dict[str, Any]) -> None:
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QHBoxLayout()
        title = QLabel(str(base_info.get("name", "-")))
        title.setStyleSheet("font-weight: 600; font-size: 16px; color: #111111;")
        badge = QLabel("Slice file")
        badge.setStyleSheet(
            "background: #f1f1f1; color: #333; padding: 4px 8px; border-radius: 10px;"
        )
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(badge)
        layout.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(16)
        self.preview = QLabel("No preview")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setFixedSize(340, 240)
        self.preview.setStyleSheet("background: #f2f2f2; border: 1px solid #dddddd; color: #666666;")
        body.addWidget(self.preview, 2)

        meta = QGridLayout()
        meta.setHorizontalSpacing(12)
        meta.setVerticalSpacing(8)
        rows = [
            ("File name", base_info.get("name")),
            ("Type", "Slice file"),
            ("Size", _format_mb(base_info.get("size_bytes"))),
            ("Time uploaded", _format_ts(base_info.get("created_at"))),
        ]
        for idx, (label, value) in enumerate(rows):
            lab = QLabel(f"{label}:")
            lab.setStyleSheet("color: #444444;")
            meta.addWidget(lab, idx, 0)
            val = QLabel(str(value) if value not in (None, "") else "-")
            val.setStyleSheet("color: #111111;")
            val.setWordWrap(True)
            meta.addWidget(val, idx, 1)
        body.addLayout(meta, 1)
        layout.addLayout(body)

        thumb_url = base_info.get("thumbnail")
        if isinstance(thumb_url, str) and thumb_url:
            self._load_preview_from_url(thumb_url)

    def _build_card_b(self, card: QFrame, gcode_info: Dict[str, Any], note: str) -> None:
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("Slicing details")
        title.setStyleSheet("font-weight: 600; color: #111111;")
        layout.addWidget(title)

        if note:
            note_label = QLabel(note)
            note_label.setStyleSheet("color: #666666;")
            layout.addWidget(note_label)

        slice_param = _parse_json(gcode_info.get("slice_param"))
        slice_result = _parse_json(gcode_info.get("slice_result"))
        src = slice_param or slice_result

        left = [
            ("Printer type", src.get("machine_name")),
            ("Print size", self._format_size(src)),
            ("Estimated printing time", _fmt_seconds_hms(src.get("estimate"))),
            ("Thickness (mm)", _fmt_float(src.get("zthick"), 2)),
            ("Lights off time(s)", _fmt_float(src.get("off_time"), 2)),
            ("Number of bottom layers", src.get("bott_layers")),
            ("Z Axis lifting speed(mm/s)", _fmt_float(src.get("zup_speed"), 2)),
        ]
        right = [
            ("Consumables", src.get("material_type") or "Resin"),
            ("Slice layers", src.get("layers")),
            (
                "Estimated amount of consumables",
                self._format_consumables(src.get("supplies_usage"), src.get("material_unit")),
            ),
            ("Exposure time(s)", _fmt_float(src.get("exposure_time"), 2)),
            ("Bottom exposure time(s)", _fmt_float(src.get("bott_time"), 2)),
            ("Z Axis lifting distance(mm)", _fmt_float(src.get("zup_height"), 2)),
            ("Z Axis fallback speed(mm/s)", _fmt_float(src.get("zdown_speed"), 2)),
        ]

        grid = QGridLayout()
        grid.setHorizontalSpacing(32)
        grid.setVerticalSpacing(8)
        for idx, (label, value) in enumerate(left):
            lab = QLabel(f"{label}:")
            lab.setStyleSheet("color: #444444;")
            grid.addWidget(lab, idx, 0)
            grid.addWidget(self._value_label(value), idx, 1)
        for idx, (label, value) in enumerate(right):
            lab = QLabel(f"{label}:")
            lab.setStyleSheet("color: #444444;")
            grid.addWidget(lab, idx, 2)
            grid.addWidget(self._value_label(value), idx, 3)

        layout.addLayout(grid)

    def _value_label(self, value: Any) -> QLabel:
        text = "-" if value in (None, "") else str(value)
        lab = QLabel(text)
        lab.setStyleSheet("color: #111111;")
        return lab

    def _load_preview_from_url(self, url: str) -> None:
        def work():
            return fetch_image_bytes(url, timeout=20.0)

        def done(data: bytes):
            if not data:
                return
            image = QImage()
            image.loadFromData(data)
            if image.isNull():
                return
            pix = QPixmap.fromImage(image)
            self.preview.setPixmap(pix.scaled(240, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        self._runner.run(work, on_result=done)

    def _format_consumables(self, value: Any, unit: Optional[str]) -> str:
        num = _fmt_float(value, 2)
        if num == "-":
            return "-"
        return f"{num}{unit or 'ml'}"

    def _format_size(self, src: Dict[str, Any]) -> str:
        try:
            x = float(src.get("size_x") or 0)
            y = float(src.get("size_y") or 0)
            z = float(src.get("size_z") or 0)
        except (TypeError, ValueError):
            return "-"
        if x == 0 and y == 0:
            return "-"
        return f"{_fmt_float(x, 2)} x {_fmt_float(y, 2)} x {_fmt_float(z, 2)} mm"
