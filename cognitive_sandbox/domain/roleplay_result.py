from __future__ import annotations

from dataclasses import dataclass

from cognitive_sandbox.domain.dialogue import DialogueLine
from cognitive_sandbox.domain.narrative_event import NarrativeEvent
from cognitive_sandbox.domain.simulation_result import SimulationTickResult


@dataclass(frozen=True)
class RoleplayResult:
    turn_id: str
    action_executed: bool
    narrative_events: tuple[NarrativeEvent, ...]
    dialogue_lines: tuple[DialogueLine, ...]
    simulation_result: SimulationTickResult | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.turn_id, str) or not self.turn_id.strip():
            raise ValueError("turn_id must not be empty.")
        if not isinstance(self.action_executed, bool):
            raise TypeError("action_executed must be a boolean.")
        if self.simulation_result is not None and not isinstance(
            self.simulation_result, SimulationTickResult
        ):
            raise TypeError("simulation_result must be a SimulationTickResult or None.")
        if isinstance(self.narrative_events, (str, bytes)):
            raise TypeError("narrative_events must contain NarrativeEvent values.")
        narrative_events = tuple(self.narrative_events)
        if any(not isinstance(item, NarrativeEvent) for item in narrative_events):
            raise TypeError("narrative_events must contain only NarrativeEvent values.")
        if isinstance(self.dialogue_lines, (str, bytes)):
            raise TypeError("dialogue_lines must contain DialogueLine values.")
        dialogue_lines = tuple(self.dialogue_lines)
        if any(not isinstance(item, DialogueLine) for item in dialogue_lines):
            raise TypeError("dialogue_lines must contain only DialogueLine values.")
        object.__setattr__(self, "narrative_events", narrative_events)
        object.__setattr__(self, "dialogue_lines", dialogue_lines)
