from __future__ import annotations

import json
import re
from pathlib import Path
from threading import RLock
from typing import Mapping, Protocol
from uuid import uuid4


class SaveRepository(Protocol):
    """Storage port; application services never manipulate files directly."""

    def save_world(self, instance_id: str, document: Mapping) -> None: ...
    def load_world(self, instance_id: str) -> Mapping: ...
    def list_worlds(self) -> tuple[str, ...]: ...
    def delete_world(self, instance_id: str) -> bool: ...


class JsonSaveRepository:
    """Atomic, one-file-per-world JSON storage."""

    _SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,160}$")

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)
        self._lock = RLock()

    def save_world(self, instance_id: str, document: Mapping) -> None:
        path = self._path(instance_id)
        if not isinstance(document, Mapping):
            raise TypeError("document must be a mapping.")
        # Serialize before opening a temp file so unsupported data cannot damage a save.
        content = json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False)
        with self._lock:
            self.directory.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(f".{path.stem}.{uuid4().hex}.tmp")
            try:
                temporary.write_text(content, encoding="utf-8")
                temporary.replace(path)
            finally:
                if temporary.exists():
                    temporary.unlink()

    def load_world(self, instance_id: str) -> Mapping:
        path = self._path(instance_id)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise KeyError(f"world save not found: {instance_id}") from None
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"world save is unreadable: {instance_id}") from error
        if not isinstance(value, dict):
            raise ValueError(f"world save has an invalid document: {instance_id}")
        return value

    def list_worlds(self) -> tuple[str, ...]:
        with self._lock:
            if not self.directory.exists():
                return ()
            return tuple(sorted(path.stem for path in self.directory.glob("*.json") if self._SAFE_ID.fullmatch(path.stem)))

    def delete_world(self, instance_id: str) -> bool:
        path = self._path(instance_id)
        with self._lock:
            try:
                path.unlink()
            except FileNotFoundError:
                return False
            return True

    def _path(self, instance_id: str) -> Path:
        if not isinstance(instance_id, str) or not self._SAFE_ID.fullmatch(instance_id):
            raise ValueError("instance_id contains unsupported path characters.")
        return self.directory / f"{instance_id}.json"
