from dataclasses import dataclass
from typing import Optional


@dataclass
class FileItem:
    id: str
    name: str
    size_bytes: int
    created_at: int
    file_type: Optional[int] = None
    md5: Optional[str] = None
    url: Optional[str] = None
    thumbnail: Optional[str] = None
    gcode_id: Optional[str] = None


@dataclass
class Quota:
    total_bytes: int
    used_bytes: int

    @property
    def free_bytes(self) -> int:
        return max(self.total_bytes - self.used_bytes, 0)

    @property
    def used_percent(self) -> float:
        if self.total_bytes <= 0:
            return 0.0
        return (self.used_bytes / self.total_bytes) * 100.0
