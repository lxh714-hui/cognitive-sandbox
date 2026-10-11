from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class Constraint:
    type: str
    content: str

    ALLOWED_TYPES: ClassVar[frozenset[str]] = frozenset({"hard", "soft", "preference"})

    def __post_init__(self) -> None:
        if not isinstance(self.type, str) or self.type not in self.ALLOWED_TYPES:
            raise ValueError("type must be hard, soft, or preference.")
        if not isinstance(self.content, str) or not self.content.strip():
            raise ValueError("content must not be empty.")
