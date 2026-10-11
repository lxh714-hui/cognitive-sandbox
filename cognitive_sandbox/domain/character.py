from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable


def _string_tuple(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{field_name} must be a collection of strings.")
    normalized = tuple(values)
    if any(not isinstance(value, str) or not value.strip() for value in normalized):
        raise ValueError(f"{field_name} must contain non-empty strings.")
    return normalized


@dataclass(frozen=True)
class CharacterState:
    character_id: str
    name: str
    role: str
    traits: tuple[str, ...]
    goals: tuple[str, ...]
    fears: tuple[str, ...]
    memories: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in ("character_id", "name", "role"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty.")
        for field_name in ("traits", "goals", "fears", "memories"):
            object.__setattr__(self, field_name, _string_tuple(getattr(self, field_name), field_name))
