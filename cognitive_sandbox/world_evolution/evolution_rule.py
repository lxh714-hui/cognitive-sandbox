from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvolutionRule:
    event_type: str
    target_type: str
    field: str
    operation: str
    value: int | float | bool | str
    reason: str
    target_id: str | None = None

    def __post_init__(self):
        for name in ("event_type", "target_type", "field", "reason"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty.")
        if self.operation not in {"set", "increment"}:
            raise ValueError("operation must be set or increment.")
        if self.target_id is not None and (not isinstance(self.target_id, str) or not self.target_id.strip()):
            raise ValueError("target_id must be None or a non-empty string.")
        if self.operation == "increment" and (isinstance(self.value, bool) or not isinstance(self.value, (int, float))):
            raise TypeError("increment rules require a numeric value.")
