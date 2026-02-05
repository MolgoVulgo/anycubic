import os
from datetime import datetime
from typing import Callable, Optional

import httpx
import os
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from ...api import delete_files, get_download_url, get_gcode_info, get_quota, list_files, upload_file
from ...client import CloudClient
from ...models import FileItem
from ..threads import TaskRunner
from .file_details import FileDetailsWindow


def _format_ts(ts: int) -> str:
    if not ts:
        return "-"
    if ts > 10_000_000_000:
        ts = int(ts / 1000)
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def _format_mb(num: int) -> str:
    if not num:
        return "-"
    mb = num / (1024 ** 2)
    return f"{mb:.2f} MB"


class FileCard(QFrame):
    def __init__(
        self,
        item: FileItem,
        on_details: Callable[[FileItem], None],
        on_delete: Callable[[FileItem], None],
        on_print: Callable[[FileItem], None],
        on_download: Callable[[FileItem], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.item = item
        self._on_details = on_details
        self._on_delete = on_delete
        self._on_print = on_print
        self._on_download = on_download
        self.thumb_label = QLabel()

        self.setObjectName("fileCard")
        self.setStyleSheet(
            "#fileCard { background: #ffffff; border-radius: 10px; border: 1px solid #e6e6e6; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        thumb_wrapper = QFrame()
        thumb_wrapper.setFixedWidth(190)
        wrapper_layout = QVBoxLayout(thumb_wrapper)
        wrapper_layout.setContentsMargins(20, 20, 20, 20)
        wrapper_layout.setSpacing(0)

        thumb = QFrame()
        thumb.setFixedSize(150, 150)
        thumb.setStyleSheet("background: #1d4d8f; border-radius: 6px;")
        thumb_layout = QVBoxLayout(thumb)
        thumb_layout.setContentsMargins(6, 6, 6, 6)
        thumb_layout.addStretch(1)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        thumb_layout.addWidget(self.thumb_label, 1)
        badge = QLabel("pwmb")
        badge.setStyleSheet(
            "background: #0f376a; color: #ffffff; padding: 2px 6px; border-radius: 6px;"
        )
        thumb_layout.addWidget(badge, alignment=Qt.AlignLeft | Qt.AlignBottom)

        wrapper_layout.addWidget(thumb, alignment=Qt.AlignCenter)
        layout.addWidget(thumb_wrapper)

        header = QHBoxLayout()
        header.addStretch(1)
        delete_btn = QPushButton()
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setFlat(True)
        delete_btn.setStyleSheet("padding: 2px;")
        icon_path = os.path.join(os.path.dirname(__file__), "..", "asset", "bin.png")
        delete_btn.setIcon(QIcon(os.path.abspath(icon_path)))
        delete_btn.setIconSize(QSize(16, 16))
        delete_btn.clicked.connect(lambda: self._on_delete(self.item))
        header.addWidget(delete_btn, alignment=Qt.AlignRight)

        meta = QVBoxLayout()
        name_label = QLabel("File name :")
        name_label.setStyleSheet("color: #444444;")
        name_value = QLabel(item.name)
        name_value.setStyleSheet("font-weight: 600; color: #111111;")
        name_value.setWordWrap(True)
        meta.addLayout(header)
        meta.addWidget(name_label)
        meta.addWidget(name_value)
        size_label = QLabel(f"Size : {_format_mb(item.size_bytes)}")
        size_label.setStyleSheet("color: #444444;")
        meta.addWidget(size_label)
        time_label = QLabel(f"Add time : {_format_ts(item.created_at)}")
        time_label.setStyleSheet("color: #444444;")
        meta.addWidget(time_label)

        buttons_row = QHBoxLayout()
        details_btn = QPushButton("Details")
        details_btn.setFlat(False)
        details_btn.setStyleSheet("background: #1d6fd6; color: #ffffff;")
        details_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        details_btn.setCursor(Qt.PointingHandCursor)
        details_btn.clicked.connect(lambda: self._on_details(self.item))
        print_btn = QPushButton("Print")
        print_btn.setStyleSheet("background: #1d6fd6; color: #ffffff;")
        print_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        print_btn.setCursor(Qt.PointingHandCursor)
        print_btn.clicked.connect(lambda: self._on_print(self.item))
        download_btn = QPushButton("Download")
        download_btn.setStyleSheet("background: #1d6fd6; color: #ffffff;")
        download_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        download_btn.setCursor(Qt.PointingHandCursor)
        download_btn.clicked.connect(lambda: self._on_download(self.item))
        buttons_row.addWidget(details_btn)
        buttons_row.addWidget(print_btn)
        buttons_row.addWidget(download_btn)
        buttons_row.addStretch(1)
        meta.addLayout(buttons_row)
        meta.addStretch(1)
        layout.addLayout(meta, 1)

    def set_thumbnail(self, pixmap: QPixmap) -> None:
        self.thumb_label.setPixmap(pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))


class FilesTab(QWidget):
    def __init__(self, status_cb: Optional[Callable[[str], None]] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._status = status_cb or (lambda _msg: None)
        self._client: Optional[CloudClient] = None
        self._runner = TaskRunner()
        self._cards = {}
        self._detail_windows = []
        self._thumbs_enabled = os.getenv("ACCLOUD_DISABLE_THUMBS", "0") not in ("1", "true", "TRUE")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        header = QHBoxLayout()
        self.upload_btn = QPushButton("Upload file")
        self.upload_btn.setCursor(Qt.PointingHandCursor)
        self.upload_btn.clicked.connect(self._upload_dialog)
        header.addWidget(self.upload_btn, alignment=Qt.AlignLeft)

        self.quota_label = QLabel("Space use: -/-")
        self.quota_label.setStyleSheet("color: #666666;")
        header.addStretch(1)
        header.addWidget(self.quota_label, alignment=Qt.AlignCenter)
        header.addStretch(1)

        self.quick_btn = QPushButton("Quick import")
        self.quick_btn.setCursor(Qt.PointingHandCursor)
        self.quick_btn.clicked.connect(self._upload_dialog)
        header.addWidget(self.quick_btn, alignment=Qt.AlignRight)
        root.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        container = QWidget()
        self.list_layout = QVBoxLayout(container)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch(1)
        self.scroll.setWidget(container)
        root.addWidget(self.scroll)

    def set_client(self, client: CloudClient) -> None:
        self._client = client
        self.refresh()

    def refresh(self) -> None:
        if not self._client:
            self._status("No session loaded.")
            return
        self._status("Loading files...")
        self._runner.run(self._load_quota, on_result=self._apply_quota, on_error=self._on_error)
        self._runner.run(self._load_files, on_result=self._apply_files, on_error=self._on_error)

    def _load_quota(self):
        return get_quota(self._client)

    def _apply_quota(self, quota):
        self.quota_label.setText(f"Space use: {quota.used_bytes / (1024**3):.2f}GB/{quota.total_bytes / (1024**3):.2f}GB")
        self._status("Quota updated.")

    def _load_files(self):
        return list_files(self._client, page=1, limit=50)

    def _apply_files(self, items):
        self._clear_cards()
        for item in items:
            card = FileCard(
                item,
                on_details=self._open_details,
                on_delete=self._delete_item,
                on_print=self._print_item,
                on_download=self._download_item,
            )
            self._cards[item.id] = card
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)
            if self._thumbs_enabled and item.thumbnail:
                self._load_thumbnail(item, card)
        self._status(f"{len(items)} file(s) loaded.")

    def _clear_cards(self) -> None:
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._cards = {}

    def _upload_dialog(self) -> None:
        if not self._client:
            QMessageBox.information(self, "Upload", "Load a session first.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Select file to upload")
        if not path:
            return

        def work():
            return upload_file(self._client, path)

        def done(file_id):
            self._status(f"Upload ok (id={file_id})")
            self.refresh()

        self._runner.run(work, on_result=done, on_error=self._on_error)

    def _download_item(self, item: FileItem) -> None:
        if not self._client:
            return
        dest, _ = QFileDialog.getSaveFileName(self, "Save file as", item.name)
        if not dest:
            return

        def work():
            url = get_download_url(self._client, item.id)
            if not url:
                raise RuntimeError("No download URL returned")
            with httpx.stream("GET", url, timeout=60.0) as resp:
                resp.raise_for_status()
                with open(dest, "wb") as handle:
                    for chunk in resp.iter_bytes():
                        handle.write(chunk)
            return dest

        def done(saved):
            self._status(f"Downloaded to {saved}")

        self._runner.run(work, on_result=done, on_error=self._on_error)

    def _delete_item(self, item: FileItem) -> None:
        if not self._client:
            return
        ok = QMessageBox.question(self, "Delete", f"Delete {item.name}?")
        if ok != QMessageBox.StandardButton.Yes:
            return

        def work():
            delete_files(self._client, [item.id])
            return True

        def done(_):
            self._status("Deleted")
            self.refresh()

        self._runner.run(work, on_result=done, on_error=self._on_error)

    def _print_item(self, item: FileItem) -> None:
        QMessageBox.information(self, "Print", "Print not implemented in Qt UI yet.")

    def _open_details(self, item: FileItem) -> None:
        if not self._client:
            QMessageBox.information(self, "Details", "Load a session first.")
            return
        self._status(f"Open details for id={item.id}")
        base_info = {
            "id": item.id,
            "name": item.name,
            "size_bytes": item.size_bytes,
            "created_at": item.created_at,
            "thumbnail": item.thumbnail,
        }

        if item.gcode_id:
            def work():
                return get_gcode_info(self._client, item.gcode_id)

            def done(info):
                self._show_details_window(base_info, info, note="")

            def err(exc: Exception):
                self._show_details_window(base_info, {}, note="Some data unavailable.")
                self._on_error(exc)

            self._runner.run(work, on_result=done, on_error=err)
        else:
            self._show_details_window(base_info, {}, note="Some data unavailable.")

    def _show_details_window(self, base_info: dict, gcode_info: dict, note: str) -> None:
        if not self.isVisible():
            return
        win = FileDetailsWindow(base_info, gcode_info, note=note, parent=self)
        win.setAttribute(Qt.WA_DeleteOnClose, True)
        self._detail_windows.append(win)
        win.destroyed.connect(lambda _obj=None, w=win: self._detail_windows.remove(w) if w in self._detail_windows else None)
        win.show()

    def _load_thumbnail(self, item: FileItem, card: FileCard) -> None:
        def work():
            with httpx.stream("GET", item.thumbnail, timeout=20.0) as resp:
                resp.raise_for_status()
                return resp.read()

        def done(data: bytes):
            if not data:
                return
            image = QImage()
            image.loadFromData(data)
            if not image.isNull():
                card.set_thumbnail(QPixmap.fromImage(image))

        self._runner.run(work, on_result=done, on_error=self._on_error)

    def _on_error(self, exc: Exception) -> None:
        self._status(f"Error: {exc}")
