from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from cognitive_sandbox.application.npc.npc_action import NpcAction


@dataclass(frozen=True)
class GoalActionCandidate:
    action: NpcAction
    score: float
    source: str
    priority: float

    def __post_init__(self):
        if not isinstance(self.action, NpcAction):
            raise TypeError("action must be NpcAction.")
        for name in ("score", "priority"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1.")
            object.__setattr__(self, name, float(value))
        if self.source not in {"emergency", "goal", "routine"}:
            raise ValueError("source must be emergency, goal, or routine.")


class GoalActionGenerator:
    """Translate scenario-authored goal action definitions into candidates."""

    def __init__(self, action_rules=()):
        self.action_rules = tuple(action_rules)

    def generate(self, goal, visible_knowledge=(), relationships=(), emotion=None, cognition=None,
                 *, character_id=None, current_location=None, motivation=None):
        owner = character_id or getattr(goal, "owner_id", None)
        if not owner:
            raise ValueError("character_id is required when no goal owner is available.")
        knowledge = tuple(visible_knowledge or ())
        result = []
        for rule in self.action_rules:
            if not isinstance(rule, Mapping) or rule.get("goal_type") != getattr(goal, "goal_type", None):
                continue
            minimum = int(rule.get("minimum_visible_knowledge", 0))
            if len(knowledge) < minimum:
                continue
            action_type = rule.get("action_type")
            if not isinstance(action_type, str) or not action_type.strip():
                continue
            params = {
                key: _resolve(value, current_location)
                for key, value in dict(rule.get("parameters", {})).items()
            }
            params["goal_id"] = getattr(goal, "goal_id", "")
            params["goal_type"] = goal.goal_type
            result.append(GoalActionCandidate(
                NpcAction(owner, action_type, target=rule.get("target"), parameters=params,
                          reason=str(rule.get("reason", goal.description or goal.goal_type))),
                float(rule.get("score", .5)), "goal", float(rule.get("priority", goal.priority)),
            ))
        result.sort(key=lambda item: (-item.score, item.action.action_type, repr(item.action.parameters)))
        return tuple(result)


def _resolve(value, current_location):
    if value == "$current_location":
        return current_location
    return value
