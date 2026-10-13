from __future__ import annotations

from collections.abc import Mapping


class GoalEvaluator:
    """Evaluate named, scenario-supplied requirements without knowing their story meaning."""

    def __init__(self, condition_definitions=None):
        self.condition_definitions = dict(condition_definitions or {})

    def is_actionable(self, goal, *, world_state=None, current_time=None,
                      resource_manager=None, location_manager=None) -> bool:
        if goal.status != "active" or goal.progress >= 1:
            return False
        state = world_state or {}
        return all(self._evaluate(
            self.condition_definitions.get(name), state, current_time,
            resource_manager, location_manager,
        ) for name in goal.conditions)

    def _evaluate(self, definition, state, current_time, resources, locations):
        if definition is None:
            return False
        if isinstance(definition, bool):
            return definition
        if not isinstance(definition, Mapping):
            return False
        if "all" in definition:
            return all(self._evaluate(item, state, current_time, resources, locations)
                       for item in definition["all"])
        if "any" in definition:
            return any(self._evaluate(item, state, current_time, resources, locations)
                       for item in definition["any"])
        if "not" in definition:
            return not self._evaluate(definition["not"], state, current_time, resources, locations)

        kind = definition.get("type")
        if kind == "time_window":
            if current_time is None:
                return False
            start, end = int(definition.get("start_hour", 0)), int(definition.get("end_hour", 24))
            return start <= current_time.hour < end if start <= end else current_time.hour >= start or current_time.hour < end
        if kind == "world_state":
            actual = state.get(definition.get("field"))
        elif kind == "resource":
            if resources is None:
                return False
            actual = resources.quantity(
                str(definition.get("resource_type", "resource")),
                location_id=definition.get("location_id"),
            )
        elif kind == "location":
            location = locations.get(definition.get("location_id")) if locations is not None else None
            if location is None:
                return False
            actual = getattr(location, str(definition.get("field", "")), None)
        else:
            return False
        expected = definition.get("value")
        operator = definition.get("operator", "eq")
        return _compare(actual, expected, operator)


def _compare(actual, expected, operator):
    try:
        if operator == "eq":
            return actual == expected
        if operator == "ne":
            return actual != expected
        if operator == "lt":
            return actual < expected
        if operator == "lte":
            return actual <= expected
        if operator == "gt":
            return actual > expected
        if operator == "gte":
            return actual >= expected
    except TypeError:
        return False
    return False
