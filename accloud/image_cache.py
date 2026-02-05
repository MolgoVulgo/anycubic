import hashlib
import os
import tempfile
import threading
from collections import OrderedDict
from typing import Optional

import httpx


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value not in ("0", "false", "FALSE")


class ImageCache:
    def __init__(self) -> None:
        self.enabled = _env_bool("ACCLOUD_IMAGE_CACHE", True)
        self.cache_dir = os.getenv(
            "ACCLOUD_IMAGE_CACHE_DIR",
            os.path.join(tempfile.gettempdir(), "accloud_image_cache"),
        )
        self.max_mem_items = _env_int("ACCLOUD_IMAGE_CACHE_MEM", 64)
        self.max_disk_items = _env_int("ACCLOUD_IMAGE_CACHE_ITEMS", 256)
        self.max_disk_mb = _env_int("ACCLOUD_IMAGE_CACHE_MB", 128)
        self._lock = threading.Lock()
        self._mem: "OrderedDict[str, bytes]" = OrderedDict()

        if self.enabled:
            os.makedirs(self.cache_dir, exist_ok=True)

    def get(self, url: str) -> Optional[bytes]:
        if not self.enabled or not url:
            return None

        with self._lock:
            data = self._mem.get(url)
            if data is not None:
                self._mem.move_to_end(url)
                return data

        path = self._path_for(url)
        try:
            with open(path, "rb") as handle:
                data = handle.read()
        except FileNotFoundError:
            return None
        except OSError:
            return None

        if not data:
            return None

        try:
            os.utime(path, None)
        except OSError:
            pass

        with self._lock:
            self._mem[url] = data
            self._trim_mem_locked()

        return data

    def set(self, url: str, data: bytes) -> None:
        if not self.enabled or not url or not data:
            return
        path = self._path_for(url)
        tmp = f"{path}.tmp"

        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            with open(tmp, "wb") as handle:
                handle.write(data)
            os.replace(tmp, path)
        except OSError:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except OSError:
                pass
            return

        with self._lock:
            self._mem[url] = data
            self._trim_mem_locked()
            self._enforce_disk_limits_locked()

    def _path_for(self, url: str) -> str:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{digest}.bin")

    def _trim_mem_locked(self) -> None:
        while len(self._mem) > self.max_mem_items:
            self._mem.popitem(last=False)

    def _enforce_disk_limits_locked(self) -> None:
        if self.max_disk_items <= 0 and self.max_disk_mb <= 0:
            return

        try:
            entries = [
                (entry.path, entry.stat().st_mtime, entry.stat().st_size)
                for entry in os.scandir(self.cache_dir)
                if entry.is_file() and entry.name.endswith(".bin")
            ]
        except OSError:
            return

        total_size = sum(size for _path, _mtime, size in entries)
        max_bytes = self.max_disk_mb * 1024 * 1024

        if len(entries) <= self.max_disk_items and (max_bytes <= 0 or total_size <= max_bytes):
            return

        entries.sort(key=lambda row: row[1])
        while entries and (
            len(entries) > self.max_disk_items or (max_bytes > 0 and total_size > max_bytes)
        ):
            path, _mtime, size = entries.pop(0)
            try:
                os.remove(path)
            except OSError:
                pass
            total_size -= size


_IMAGE_CACHE = ImageCache()


def fetch_image_bytes(url: str, timeout: float = 20.0) -> bytes:
    if _IMAGE_CACHE.enabled:
        cached = _IMAGE_CACHE.get(url)
        if cached is not None:
            return cached

    with httpx.stream("GET", url, timeout=timeout) as resp:
        resp.raise_for_status()
        data = resp.read()

    if _IMAGE_CACHE.enabled and data:
        _IMAGE_CACHE.set(url, data)
    return data
