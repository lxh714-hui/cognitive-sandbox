from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from cognitive_sandbox.domain.constraint import Constraint


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
class CharacterCard:
    character_id: str
    name: str
    age: int | None = None
    gender: str = ""
    occupation: str = ""
    personality: tuple[str, ...] = ()
    background: str = ""
    goals: tuple[str, ...] = ()
    constraints: tuple[Constraint, ...] = ()
    portrait: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("character_id", "name"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty.")
        if self.age is not None and (
            isinstance(self.age, bool) or not isinstance(self.age, int) or self.age < 0
        ):
            raise ValueError("age must be a non-negative integer or None.")
        for field_name in ("gender", "occupation", "background"):
            if not isinstance(getattr(self, field_name), str):
                raise TypeError(f"{field_name} must be a string.")
        if self.portrait is not None and not isinstance(self.portrait, str):
            raise TypeError("portrait must be a string or None.")

        for field_name in ("personality", "goals"):
            object.__setattr__(self, field_name, _string_tuple(getattr(self, field_name), field_name))
        if isinstance(self.constraints, (str, bytes)):
            raise TypeError("constraints must be a collection of Constraint values.")
        try:
            constraints = tuple(self.constraints)
        except TypeError as error:
            raise TypeError("constraints must be a collection of Constraint values.") from error
        if any(not isinstance(item, Constraint) for item in constraints):
            raise TypeError("constraints must contain only Constraint values.")
        object.__setattr__(self, "constraints", constraints)
