from __future__ import annotations

from dataclasses import dataclass
import math
from collections.abc import Iterable


def _strings(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{field_name} must be a collection of strings.")
    result = tuple(values)
    if any(not isinstance(value, str) or not value.strip() for value in result):
        raise ValueError(f"{field_name} must contain non-empty strings.")
    return result


@dataclass(frozen=True)
class WorldFact:
    """An objective world fact; it does not imply that any character knows it."""

    id: str
    content: str
    fact_type: str
    timestamp: str
    related_entities: tuple[str, ...] = ()
    importance: float = 0.5

    def __post_init__(self) -> None:
        for name in ("id", "content", "fact_type", "timestamp"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        object.__setattr__(self, "related_entities", _strings(self.related_entities, "related_entities"))
        if isinstance(self.importance, bool) or not isinstance(self.importance, (int, float)):
            raise TypeError("importance must be between 0 and 1.")
        if not math.isfinite(self.importance) or not 0 <= self.importance <= 1:
            raise ValueError("importance must be between 0 and 1.")
        object.__setattr__(self, "importance", float(self.importance))
