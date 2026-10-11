from __future__ import annotations

from collections.abc import Mapping
import math
from types import MappingProxyType
from typing import Any

from cognitive_sandbox.domain.world_transition import WorldStateTransition


def _copy_and_freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("world_state keys must be strings.")
        return MappingProxyType({key: _copy_and_freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_copy_and_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_copy_and_freeze(item) for item in value)
    return value


class WorldStateApplier:
    """Apply a transition to a detached copy, returning recursively read-only state."""

    def apply(
        self,
        current_world_state: Mapping[str, Any],
        transition: WorldStateTransition,
    ) -> Mapping[str, Any]:
        if not isinstance(current_world_state, Mapping):
            raise TypeError("current_world_state must be a mapping.")
        if not isinstance(transition, WorldStateTransition):
            raise TypeError("transition must be a WorldStateTransition.")

        updated = {key: _copy_and_freeze(value) for key, value in current_world_state.items()}
        for key, delta in transition.changed_state.items():
            current = updated.get(key)
            if (
                isinstance(delta, (int, float))
                and not isinstance(delta, bool)
                and isinstance(current, (int, float))
                and not isinstance(current, bool)
            ):
                total = current + delta
                if isinstance(total, float) and not math.isfinite(total):
                    raise ValueError(f"Applying transition produced a non-finite value for {key}.")
                updated[key] = total
            else:
                updated[key] = _copy_and_freeze(delta)
        return MappingProxyType(updated)
