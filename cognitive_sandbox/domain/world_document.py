from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


def _string_tuple(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{field_name} must be a collection of strings.")
    try:
        items = tuple(values)
    except TypeError as error:
        raise TypeError(f"{field_name} must be a collection of strings.") from error
    if any(not isinstance(item, str) or not item.strip() for item in items):
        raise ValueError(f"{field_name} must contain non-empty strings.")
    return items


@dataclass(frozen=True)
class WorldDocument:
    world_id: str
    name: str
    description: str
    history: tuple[str, ...] = ()
    rules: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("world_id", "name", "description"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty.")
        for field_name in ("history", "rules"):
            object.__setattr__(self, field_name, _string_tuple(getattr(self, field_name), field_name))
