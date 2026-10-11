from __future__ import annotations

from cognitive_sandbox.domain.simulation import EventImportance, SimulationMode


class SimulationPolicy:
    """Map event importance to a simulation mode without running that mode."""

    DEEP_REASONING_THRESHOLD = 0.95

    def select_mode(self, importance: EventImportance) -> SimulationMode:
        if not isinstance(importance, EventImportance):
            raise TypeError("importance must be an EventImportance.")
        if importance.level == "low":
            return SimulationMode.RULE_ONLY
        if importance.level == "medium":
            return SimulationMode.BASIC_COGNITION
        if importance.score >= self.DEEP_REASONING_THRESHOLD:
            return SimulationMode.DEEP_REASONING
        return SimulationMode.FULL_COGNITION

    @staticmethod
    def should_run_rules(mode: SimulationMode) -> bool:
        if not isinstance(mode, SimulationMode):
            raise TypeError("mode must be a SimulationMode.")
        # Rule simulation is the mandatory baseline for every processing mode.
        return True
