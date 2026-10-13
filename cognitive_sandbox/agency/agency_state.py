from __future__ import annotations

from dataclasses import dataclass, field, replace
from types import MappingProxyType
from collections.abc import Mapping

from .character_agency import CharacterAgency


@dataclass(frozen=True)
class AgencyState:
    """Immutable save snapshot of agency values, routine counters and action history."""

    agencies: tuple[CharacterAgency, ...] = ()
    routine_progress: Mapping[str, int] = field(default_factory=dict)
    autonomous_action_history: tuple[tuple[str, str, str], ...] = ()
    action_feedback_history: tuple[tuple[str, str, str, str, float], ...] = ()

    def __post_init__(self):
        agencies = tuple(self.agencies)
        if any(not isinstance(item, CharacterAgency) for item in agencies):
            raise TypeError("agencies must contain CharacterAgency values.")
        ids = [item.character_id for item in agencies]
        if len(ids) != len(set(ids)):
            raise ValueError("agency character IDs must be unique.")
        object.__setattr__(self, "agencies", agencies)
        progress = dict(self.routine_progress)
        if any(not isinstance(key, str) or not key.strip() or isinstance(value, bool)
               or not isinstance(value, int) or value < 0 for key, value in progress.items()):
            raise ValueError("routine_progress must map non-empty IDs to non-negative integers.")
        object.__setattr__(self, "routine_progress", MappingProxyType(progress))
        history = tuple(tuple(item) for item in self.autonomous_action_history)
        if any(len(item) != 3 or any(not isinstance(part, str) or not part.strip() for part in item)
               for item in history):
            raise ValueError("autonomous_action_history entries must be (character, action, time).")
        object.__setattr__(self, "autonomous_action_history", history)
        feedback = tuple(tuple(item) for item in self.action_feedback_history)
        if any(len(item) != 5 or any(not isinstance(part, str) or not part.strip() for part in item[:4])
               or isinstance(item[4], bool) or not isinstance(item[4], (int, float)) or not 0 <= item[4] <= 1
               for item in feedback):
            raise ValueError("action_feedback_history entries must be (character, action, time, result, effectiveness).")
        object.__setattr__(self, "action_feedback_history", tuple((*item[:4], float(item[4])) for item in feedback))


class AgencyStateManager:
    """Mutable runtime owner which exposes immutable state snapshots."""

    def __init__(self, state: AgencyState | None = None, character_ids=()):
        if state is not None and not isinstance(state, AgencyState):
            raise TypeError("state must be AgencyState.")
        self._agencies = {item.character_id: item for item in (state.agencies if state else ())}
        self._routine_progress = dict(state.routine_progress if state else {})
        self._history = list(state.autonomous_action_history if state else ())
        self._feedback = list(state.action_feedback_history if state else ())
        for character_id in character_ids:
            self.ensure(character_id)

    def ensure(self, character_id: str, *, initiative=.55, motivation_strength=.5, goal_focus=.5):
        if character_id not in self._agencies:
            self._agencies[character_id] = CharacterAgency(
                character_id, initiative, motivation_strength, goal_focus, 0.0, None,
            )
        return self._agencies[character_id]

    def get(self, character_id: str) -> CharacterAgency:
        return self.ensure(character_id)

    @property
    def states(self) -> tuple[CharacterAgency, ...]:
        return tuple(self._agencies[key] for key in sorted(self._agencies))

    def routine_count(self, key: str) -> int:
        return self._routine_progress.get(key, 0)

    def record_routine(self, key: str) -> None:
        self._routine_progress[key] = self._routine_progress.get(key, 0) + 1

    def record_action(self, character_id: str, action_type: str, when: str, *,
                      result: str = "completed", effectiveness: float = 0.5) -> CharacterAgency:
        if not isinstance(result, str) or not result.strip():
            raise ValueError("result must not be empty.")
        if isinstance(effectiveness, bool) or not isinstance(effectiveness, (int, float)) or not 0 <= effectiveness <= 1:
            raise ValueError("effectiveness must be between 0 and 1.")
        old = self.ensure(character_id)
        # A bounded moving rate: recent activity raises frequency without allowing
        # one busy day to permanently dominate a long-running world.
        updated = replace(old, action_frequency=min(1.0, old.action_frequency * .8 + .2),
                          last_action_time=when)
        self._agencies[character_id] = updated
        self._history.append((character_id, action_type, when))
        self._history = self._history[-500:]
        self._feedback.append((character_id, action_type, when, result, float(effectiveness)))
        self._feedback = self._feedback[-500:]
        return updated

    @property
    def action_feedback_history(self):
        return tuple(self._feedback)

    def snapshot(self) -> AgencyState:
        return AgencyState(self.states, self._routine_progress, tuple(self._history), tuple(self._feedback))
