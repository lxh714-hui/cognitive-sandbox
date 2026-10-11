from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


def _string_tuple(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{field_name} must be a collection of strings.")
    result = tuple(values)
    if any(not isinstance(value, str) or not value.strip() for value in result):
        raise ValueError(f"{field_name} must contain non-empty strings.")
    return result


@dataclass(frozen=True)
class CharacterDevelopmentState:
    character_id: str
    trait_growth: tuple[str, ...]
    value_growth: tuple[str, ...]
    experience_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.character_id, str) or not self.character_id.strip():
            raise ValueError("character_id must not be empty.")
        if isinstance(self.experience_count, bool) or not isinstance(self.experience_count, int):
            raise TypeError("experience_count must be a non-negative integer.")
        if self.experience_count < 0:
            raise ValueError("experience_count must be non-negative.")
        object.__setattr__(self, "trait_growth", _string_tuple(self.trait_growth, "trait_growth"))
        object.__setattr__(self, "value_growth", _string_tuple(self.value_growth, "value_growth"))
