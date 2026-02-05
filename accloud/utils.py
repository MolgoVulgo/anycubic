import logging
import os
import re
import tarfile
from datetime import datetime
from typing import Any, Dict, Optional


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


_LOG_ROTATION_CACHE: Dict[str, datetime.date] = {}


def _rotation_date_for_path(path: str) -> Optional[datetime.date]:
    cached = _LOG_ROTATION_CACHE.get(path)
    if cached is not None:
        return cached
    try:
        stat = os.stat(path)
    except FileNotFoundError:
        return None
    except OSError:
        return None
    return datetime.fromtimestamp(stat.st_mtime).date()


def _rotate_log_if_needed(
    path: str,
    today: datetime.date,
    keep_days: int,
    compress: bool,
) -> None:
    current_date = _rotation_date_for_path(path)
    if current_date is None or current_date == today:
        return

    base_dir = os.path.dirname(path) or "."
    base_name = os.path.basename(path)
    date_str = current_date.strftime("%Y-%m-%d")
    rotated_name = f"{base_name}.{date_str}.log"
    rotated_path = os.path.join(base_dir, rotated_name)

    suffix = 1
    while os.path.exists(rotated_path):
        rotated_name = f"{base_name}.{date_str}-{suffix}.log"
        rotated_path = os.path.join(base_dir, rotated_name)
        suffix += 1

    try:
        os.replace(path, rotated_path)
    except OSError:
        return

    if compress:
        archive_name = rotated_name.replace(".log", ".tar.gz")
        archive_path = os.path.join(base_dir, archive_name)
        try:
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(rotated_path, arcname=rotated_name)
            os.remove(rotated_path)
        except OSError:
            pass

    if keep_days > 0:
        _cleanup_archives(base_dir, base_name, keep_days)


def _cleanup_archives(base_dir: str, base_name: str, keep_days: int) -> None:
    pattern = re.compile(rf"^{re.escape(base_name)}\.(\d{{4}}-\d{{2}}-\d{{2}})(?:-\d+)?\.tar\.gz$")
    cutoff = datetime.now().date().toordinal() - keep_days
    try:
        entries = list(os.scandir(base_dir))
    except OSError:
        return

    for entry in entries:
        if not entry.is_file():
            continue
        match = pattern.match(entry.name)
        if not match:
            continue
        try:
            dt = datetime.strptime(match.group(1), "%Y-%m-%d").date()
        except ValueError:
            continue
        if dt.toordinal() <= cutoff:
            try:
                os.remove(entry.path)
            except OSError:
                pass


def append_log_line(
    path: str,
    line: str,
    *,
    rotate_daily: bool = False,
    keep_days: int = 7,
    compress: bool = False,
) -> None:
    now = datetime.now()
    if rotate_daily:
        _rotate_log_if_needed(path, now.date(), keep_days, compress)
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    safe_line = line.rstrip("\n")
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {safe_line}\n")
    _LOG_ROTATION_CACHE[path] = now.date()


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
