from __future__ import annotations

from collections.abc import Mapping

from cognitive_sandbox.application.npc.npc_action import NpcAction


class NpcActionGenerator:
    """Create candidates from scenario-supplied goal-to-action definitions."""

    def __init__(self, action_rules=()):
        self.action_rules = tuple(action_rules)

    def generate(self, character_mind, goals, *, current_time, owner_id=None,
                 world_state=None, resource_manager=None):
        owner_id = owner_id or getattr(character_mind, "character_id", None)
        if owner_id is None:
            owner_id = getattr(getattr(character_mind, "knowledge_context", None), "owner_id", None)
        if owner_id is None:
            owner_id = getattr(getattr(character_mind, "relationship_context", None), "owner_id", None)
        if owner_id is None:
            return ()
        owned = {goal.goal_type: goal for goal in goals if goal.owner_id == owner_id}
        result = []
        for rule in self.action_rules:
            if not isinstance(rule, Mapping):
                continue
            goal_type = rule.get("goal_type")
            goal = owned.get(goal_type)
            if goal is None or goal.status != "active" or goal.progress >= 1:
                continue
            if not _requirements_met(rule.get("requires", ()), world_state or {}, current_time, resource_manager):
                continue
            parameters = {
                key: _configured_value(value, world_state or {})
                for key, value in dict(rule.get("parameters", {})).items()
            }
            for key in ("event_lifecycle", "cooldown_days", "event_importance", "description"):
                if key in rule:
                    parameters[key] = rule[key]
            result.append(NpcAction(
                owner_id, str(rule["action_type"]), target=rule.get("target"),
                parameters=parameters,
                reason=str(rule.get("reason", goal.description or goal.goal_type)),
            ))
        return tuple(result)

    def generate_for(self, owner_id, goals, *, current_time, world_state=None, resource_manager=None):
        return self.generate(None, goals, current_time=current_time, owner_id=owner_id,
                             world_state=world_state, resource_manager=resource_manager)


def _requirements_met(requirements, world_state, current_time, resource_manager):
    if isinstance(requirements, Mapping):
        requirements = (requirements,)
    for requirement in requirements:
        if not isinstance(requirement, Mapping):
            continue
        kind = requirement.get("type")
        if kind == "world_state":
            if world_state.get(requirement.get("field")) != requirement.get("value"):
                return False
        elif kind == "resource":
            if resource_manager is None:
                return False
            amount = resource_manager.quantity(
                str(requirement.get("resource_type", "resource")),
                location_id=requirement.get("location_id"),
            )
            operator = requirement.get("operator", "gte")
            target = requirement.get("value", 0)
            comparisons = {"gte": amount >= target, "gt": amount > target,
                           "lte": amount <= target, "lt": amount < target,
                           "eq": amount == target, "ne": amount != target}
            if not comparisons.get(operator, False):
                return False
        elif kind == "time_window":
            if current_time is None:
                return False
            start, end = int(requirement.get("start_hour", 0)), int(requirement.get("end_hour", 24))
            matches = start <= current_time.hour < end if start <= end else current_time.hour >= start or current_time.hour < end
            if not matches:
                return False
    return True


def _configured_value(value, world_state):
    if isinstance(value, str) and value.startswith("$world."):
        return world_state.get(value.partition(".")[2])
    return value
