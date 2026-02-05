import faulthandler
import os
import sys

from PySide6.QtWidgets import QApplication

from .qt_app import MainWindow
from ..utils import append_log_line, get_logger


def main() -> int:
    logger = get_logger("accloud.qt")
    if os.getenv("ACCLOUD_DEBUG", "0") in ("1", "true", "TRUE"):
        logger.setLevel("DEBUG")
    fault_log = os.path.join(os.getcwd(), "accloud_fault.log")
    if os.getenv("ACCLOUD_FAULTHANDLER", "1") not in ("0", "false", "FALSE"):
        try:
            fh = open(fault_log, "a", buffering=1, encoding="utf-8")
            faulthandler.enable(file=fh, all_threads=True)
            append_log_line(fault_log, "faulthandler enabled")
            logger.info("Faulthandler enabled -> %s", fault_log)
        except Exception as exc:
            logger.info("Faulthandler enable failed: %s", exc)
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
