from __future__ import annotations


class GoalEvaluator:
    """Small deterministic eligibility checks; it never invents or rewrites goals."""

    def is_actionable(self, goal, *, world_state=None, current_time=None, resource_manager=None, location_manager=None) -> bool:
        if goal.status != "active" or goal.progress >= 1:
            return False
        conditions = tuple(item.casefold() for item in goal.conditions)
        if not conditions:
            return True
        state = world_state or {}
        for condition in conditions:
            if condition == "patrol_time":
                if current_time is None or current_time.hour not in range(18, 24) and current_time.hour not in range(0, 6):
                    return False
            elif condition == "materials_needed" and state.get("clinic_repaired") is True:
                return False
            elif condition == "materials_needed" and resource_manager is not None and resource_manager.quantity("medical_supplies") >= 1:
                return False
            elif condition == "materials_available" and (resource_manager is None or resource_manager.quantity("medical_supplies") < 1):
                return False
            elif condition == "clinic_power_restored" and location_manager is not None:
                clinic = location_manager.get("clinic")
                if clinic is not None and clinic.power is True:
                    return False
            elif condition.startswith("state:"):
                key, _, expected = condition[6:].partition("=")
                if key not in state or str(state[key]) != expected:
                    return False
        return True
