from __future__ import annotations

from dataclasses import dataclass

from .emotional_state import EmotionalState


@dataclass(frozen=True)
class EmotionThreshold:
    guilt: float = 0.8
    fear: float = 0.85
    anger: float = 0.8

    def __post_init__(self):
        for name in ("guilt", "fear", "anger"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"{name} threshold must be between 0 and 1.")


class EmotionModel:
    """Convert continuous emotion and emotional memories into soft action-score modifiers."""

    def __init__(self, thresholds=None):
        self.thresholds = thresholds or EmotionThreshold()

    def score_modifier(self, action_type: str, state: EmotionalState, memories=()) -> float:
        if not isinstance(state, EmotionalState):
            raise TypeError("state must be EmotionalState.")
        action = action_type.casefold()
        values = {
            "investigate": state.curiosity * 0.22 + state.hope * 0.06 - state.fear * 0.08,
            "escape": state.fear * 0.25 + state.despair * 0.12 - state.confidence * 0.1,
            "protect": state.attachment * 0.2 + state.guilt * 0.15 + state.hope * 0.05,
            "dangerous_protection": state.guilt * 0.18 + state.attachment * 0.14,
            "panic_escape": state.fear * 0.22 + state.stress * 0.1,
            "confrontation": state.anger * 0.24 + state.pride * 0.04,
            "observe": state.curiosity * 0.12 + state.calmness * 0.08 - state.fatigue * 0.08,
            "warn": state.fear * 0.08 + state.confidence * 0.04,
        }
        score = values.get(action, 0.0)
        tendency_map = {
            "protective": {"protect", "dangerous_protection"},
            "cautious": {"escape", "panic_escape", "observe"},
            "confrontational": {"confrontation", "warn"},
            "investigative": {"investigate", "observe"},
        }
        for memory in memories:
            if action in tendency_map.get(memory.learned_tendency, set()):
                score += 0.08 * memory.persistence
        return max(-0.5, min(0.5, score))

    def threshold_actions(self, state: EmotionalState) -> tuple[tuple[str, float], ...]:
        actions = []
        if state.guilt > self.thresholds.guilt:
            actions.append(("dangerous_protection", 0.25 + state.guilt * 0.15))
        if state.fear > self.thresholds.fear:
            actions.append(("panic_escape", 0.25 + state.fear * 0.15))
        if state.anger > self.thresholds.anger:
            actions.append(("confrontation", 0.25 + state.anger * 0.15))
        return tuple(actions)
