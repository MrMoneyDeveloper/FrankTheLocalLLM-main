from pathlib import Path
import json
from typing import Dict, Optional

class Cache:
    """Simple file-backed cache."""

    def __init__(self, path: Path):
        self.path = path
        self._data: Dict[str, str] = {}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text())
            except json.JSONDecodeError:
                self._data = {}

    def get(self, key: str) -> Optional[str]:
        return self._data.get(key)

    def set(self, key: str, value: str) -> None:
        self._data[key] = value
        self.path.write_text(json.dumps(self._data))
