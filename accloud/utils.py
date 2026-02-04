import logging
from datetime import datetime
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


def redact_payload(payload: Any) -> Any:
    if not isinstance(payload, (dict, list)):
        return payload
    secret_keys = (
        "accesskey",
        "secretkey",
        "sessiontoken",
        "token",
        "authorization",
        "awsaccesskey",
        "awssecretkey",
        "cookie",
        "agora_token",
        "shengwang",
    )
    if isinstance(payload, list):
        return [redact_payload(item) for item in payload]
    redacted: Dict[str, Any] = {}
    for key, value in payload.items():
        key_l = str(key).lower()
        if any(k in key_l for k in secret_keys):
            redacted[key] = "***"
        else:
            redacted[key] = redact_payload(value)
    return redacted


def append_log_line(path: str, line: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    safe_line = line.rstrip("\n")
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {safe_line}\n")


def truncate_text(text: str, limit: int = 2000) -> str:
    if text is None:
        return ""
    if len(text) <= limit:
        return text
    return f"{text[:limit]}...[truncated {len(text) - limit} chars]"


def format_bytes(num: int) -> str:
    step = 1024.0
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(num)
    for unit in units:
        if size < step:
            return f"{size:.2f}{unit}"
        size /= step
    return f"{size:.2f}PB"
