from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ...api import list_files, upload_file
from ...client import CloudClient
from ...models import FileItem
from ..threads import TaskRunner


class UploadDialog(QDialog):
    def __init__(self, client: CloudClient, parent=None) -> None:
        super().__init__(parent)
        self._client = client
        self._runner = TaskRunner()
        self._path: Optional[str] = None
        self._file_item: Optional[FileItem] = None
        self._print_after = False
        self._delete_after = False

        self.setWindowTitle("Upload")
        self.setModal(True)
        self.setFixedSize(520, 260)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        file_row = QHBoxLayout()
        self.file_btn = QPushButton("Choose file")
        self.file_btn.setCursor(Qt.PointingHandCursor)
        self.file_btn.clicked.connect(self._choose_file)
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color: #666666;")
        self.file_label.setWordWrap(True)
        file_row.addWidget(self.file_btn)
        file_row.addWidget(self.file_label, 1)
        root.addLayout(file_row)

        self.print_check = QCheckBox("Imprimer apres upload")
        self.delete_check = QCheckBox("Supprimer le fichier apres impression")
        self.delete_check.setEnabled(False)
        self.print_check.toggled.connect(self._on_print_toggled)
        root.addWidget(self.print_check)
        root.addWidget(self.delete_check)

        footer = QHBoxLayout()
        footer.addStretch(1)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.upload_btn = QPushButton("Upload")
        self.upload_btn.setCursor(Qt.PointingHandCursor)
        self.upload_btn.clicked.connect(self._start_upload)
        footer.addWidget(self.cancel_btn)
        footer.addWidget(self.upload_btn)
        root.addLayout(footer)

    def _choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select file to upload")
        if not path:
            return
        self._path = path
        self.file_label.setText(path)

    def _on_print_toggled(self, checked: bool) -> None:
        self.delete_check.setEnabled(checked)
        if not checked:
            self.delete_check.setChecked(False)

    def _set_busy(self, busy: bool) -> None:
        self.upload_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(not busy)
        self.file_btn.setEnabled(not busy)
        self.print_check.setEnabled(not busy)
        self.delete_check.setEnabled(not busy and self.print_check.isChecked())

    def _start_upload(self) -> None:
        if not self._path:
            QMessageBox.information(self, "Upload", "Choisissez un fichier.")
            return
        self._set_busy(True)

        def work():
            file_id = upload_file(self._client, self._path)
            items = list_files(self._client, page=1, limit=50)
            match = next((item for item in items if str(item.id) == str(file_id)), None)
            return file_id, match

        def done(result):
            file_id, match = result
            if match is None:
                name = self._path.split("/")[-1]
                match = FileItem(id=str(file_id), name=name, size_bytes=0, created_at=0)
            self._file_item = match
            self._print_after = self.print_check.isChecked()
            self._delete_after = self.delete_check.isChecked()
            self.accept()

        def err(exc: Exception) -> None:
            QMessageBox.information(self, "Upload", f"Upload failed: {exc}")
            self._set_busy(False)

        self._runner.run(work, on_result=done, on_error=err)

    def result_data(self) -> dict:
        return {
            "file_item": self._file_item,
            "print_after": self._print_after,
            "delete_after": self._delete_after,
        }
