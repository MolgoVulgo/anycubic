from dataclasses import dataclass, field
from typing import Dict, Optional

from ..client import CloudClient
from ..models import FileItem


@dataclass
class AppState:
    client: Optional[CloudClient] = None
    session_path: Optional[str] = None
    files_by_id: Dict[str, FileItem] = field(default_factory=dict)
