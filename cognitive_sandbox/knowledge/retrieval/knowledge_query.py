from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeQuery:
    text: str = ""
    tags: tuple[str, ...] = ()
    related_entities: tuple[str, ...] = ()
    limit: int = 10

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):
            raise TypeError("text must be a string.")
        for name in ("tags", "related_entities"):
            values = getattr(self, name)
            if isinstance(values, (str, bytes)):
                raise TypeError(f"{name} must be a collection of strings.")
            values = tuple(values)
            if any(not isinstance(value, str) or not value.strip() for value in values):
                raise ValueError(f"{name} must contain non-empty strings.")
            object.__setattr__(self, name, values)
        if isinstance(self.limit, bool) or not isinstance(self.limit, int) or self.limit < 0:
            raise ValueError("limit must be a non-negative integer.")
