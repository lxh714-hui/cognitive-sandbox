from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RuntimeMode(str, Enum):
    ROLEPLAY = "roleplay"
    STORY_SIMULATION = "story_simulation"


@dataclass(frozen=True)
class StorySimulationConfig:
    """Immutable scope for a story-simulation run, independent of the UI runtime."""

    world_id: str
    branch_id: str
    initial_world_revision: int = 0

    @property
    def mode(self) -> RuntimeMode:
        return RuntimeMode.STORY_SIMULATION

    def __post_init__(self) -> None:
        for name in ("world_id", "branch_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        revision = self.initial_world_revision
        if isinstance(revision, bool) or not isinstance(revision, int):
            raise TypeError("initial_world_revision must be an integer.")
        if revision < 0:
            raise ValueError("initial_world_revision must be non-negative.")
