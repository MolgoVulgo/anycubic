import os
from typing import Any, Callable, Optional

from PySide6.QtCore import Qt, QThread

from ..utils import get_logger
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class WorkerSignals(QObject):
    finished = Signal()
    error = Signal(Exception)
    result = Signal(object)


class Worker(QRunnable):
    def __init__(self, fn: Callable[[], Any]) -> None:
        super().__init__()
        self.fn = fn
        self.signals = WorkerSignals()
        self.logger = get_logger("accloud.qt")
        if os.getenv("ACCLOUD_DEBUG", "0") in ("1", "true", "TRUE"):
            self.logger.setLevel("DEBUG")

    @Slot()
    def run(self) -> None:
        self.logger.debug("Worker start thread=%s", QThread.currentThread())
        try:
            result = self.fn()
        except Exception as exc:
            self.logger.debug("Worker error thread=%s exc=%s", QThread.currentThread(), exc)
            self.signals.error.emit(exc)
        else:
            self.logger.debug("Worker result thread=%s", QThread.currentThread())
            self.signals.result.emit(result)
        finally:
            self.logger.debug("Worker finished thread=%s", QThread.currentThread())
            self.signals.finished.emit()


class TaskRunner:
    def __init__(self) -> None:
        self.pool = QThreadPool.globalInstance()
        self.logger = get_logger("accloud.qt")
        if os.getenv("ACCLOUD_DEBUG", "0") in ("1", "true", "TRUE"):
            self.logger.setLevel("DEBUG")
        self._workers = set()

    def run(
        self,
        fn: Callable[[], Any],
        on_result: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        on_finished: Optional[Callable[[], None]] = None,
    ) -> Worker:
        worker = Worker(fn)
        self._workers.add(worker)
        if on_result:
            worker.signals.result.connect(on_result, Qt.QueuedConnection)
        if on_error:
            worker.signals.error.connect(on_error, Qt.QueuedConnection)
        if on_finished:
            worker.signals.finished.connect(on_finished, Qt.QueuedConnection)
        worker.signals.finished.connect(lambda: self._workers.discard(worker), Qt.QueuedConnection)
        self.logger.debug("TaskRunner start worker thread=%s", QThread.currentThread())
        self.pool.start(worker)
        return worker
