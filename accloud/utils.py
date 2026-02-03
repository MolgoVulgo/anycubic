import logging
from typing import Any, Dict


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def redacted_headers(headers: Dict[str, Any]) -> Dict[str, Any]:
    redacted = {}
    for k, v in headers.items():
        if k.lower() in ('authorization', 'cookie'):
            redacted[k] = '[REDACTED]'
        else:
            redacted[k] = v
    return redacted


def format_bytes(num: int) -> str:
    step = 1024.0
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(num)
    for unit in units:
        if size < step:
            return f"{size:.2f}{unit}"
        size /= step
    return f"{size:.2f}PB"
