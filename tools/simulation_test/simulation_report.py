from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from tools.simulation_test.simulation_metrics import SimulationMetrics


@dataclass(frozen=True)
class CharacterSimulationSummary:
    character_id: str
    action_count: int = 0
    goal_changes: tuple[str, ...] = ()
    emotion_changes: tuple[Any, ...] = ()
    relationship_changes: tuple[Any, ...] = ()
    cognition_changes: tuple[Any, ...] = ()
    development_changes: tuple[Any, ...] = ()
    state_summary: Any = None
    progress_velocity: float = 0.0
    stagnation_level: float = 0.0
    frustration_level: float = 0.0

    def __post_init__(self):
        if not isinstance(self.character_id, str) or not self.character_id.strip():
            raise ValueError("character_id must not be empty.")
        if isinstance(self.action_count, bool) or not isinstance(self.action_count, int) or self.action_count < 0:
            raise ValueError("action_count must be a non-negative integer.")
        for name in ("goal_changes", "emotion_changes", "relationship_changes", "cognition_changes", "development_changes"):
            object.__setattr__(self, name, tuple(getattr(self, name)))
        for name in ("progress_velocity", "stagnation_level", "frustration_level"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
            object.__setattr__(self, name, float(value))


@dataclass(frozen=True)
class ThreadStateChange:
    thread_id: str
    title: str
    before_status: str
    after_status: str
    before_progress: float
    after_progress: float
    before_conflict: str = ""
    after_conflict: str = ""
    before_pressure: float = 0.0
    after_pressure: float = 0.0


@dataclass(frozen=True)
class NarrativeThreadSummary:
    thread_id: str
    title: str
    status: str
    progress: float
    pressure: float
    participants: tuple[str, ...]
    conflict: str = ""

    def __post_init__(self):
        object.__setattr__(self, "participants", tuple(self.participants))


@dataclass(frozen=True)
class SimulationReport:
    world_instance_id: str
    world_name: str
    ticks: int
    start_time: str
    end_time: str
    elapsed_seconds: float
    events: tuple[Any, ...]
    state_changes: tuple[Any, ...]
    characters: Mapping[str, CharacterSimulationSummary]
    thread_states: tuple[NarrativeThreadSummary, ...]
    thread_changes: tuple[ThreadStateChange, ...]
    director_constraints: tuple[Any, ...]
    candidate_events: tuple[Any, ...]
    metrics: SimulationMetrics
    random_seed: int
    player_idle_enabled: bool
    goal_transitions: tuple[Any, ...] = ()
    relationship_transitions: tuple[Any, ...] = ()
    relationship_stages: tuple[Any, ...] = ()
    encounter_candidates: tuple[Any, ...] = ()
    encounters: tuple[Any, ...] = ()
    narrative_pressure: Any = None
    conflicts: tuple[Any, ...] = ()

    def __post_init__(self):
        for name in ("world_instance_id", "world_name", "start_time", "end_time"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty.")
        if isinstance(self.ticks, bool) or not isinstance(self.ticks, int) or self.ticks < 0:
            raise ValueError("ticks must be a non-negative integer.")
        if self.elapsed_seconds < 0:
            raise ValueError("elapsed_seconds must be non-negative.")
        object.__setattr__(self, "events", tuple(self.events))
        object.__setattr__(self, "state_changes", tuple(self.state_changes))
        object.__setattr__(self, "thread_states", tuple(self.thread_states))
        object.__setattr__(self, "thread_changes", tuple(self.thread_changes))
        object.__setattr__(self, "director_constraints", tuple(self.director_constraints))
        object.__setattr__(self, "candidate_events", tuple(self.candidate_events))
        object.__setattr__(self, "goal_transitions", tuple(self.goal_transitions))
        object.__setattr__(self, "relationship_transitions", tuple(self.relationship_transitions))
        object.__setattr__(self, "relationship_stages", tuple(self.relationship_stages))
        object.__setattr__(self, "encounter_candidates", tuple(self.encounter_candidates))
        object.__setattr__(self, "encounters", tuple(self.encounters))
        object.__setattr__(self, "conflicts", tuple(self.conflicts))
        object.__setattr__(self, "characters", MappingProxyType(dict(self.characters)))
