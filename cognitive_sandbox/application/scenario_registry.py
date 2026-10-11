from __future__ import annotations

from cognitive_sandbox.domain.scenario import Scenario


class ScenarioRegistry:
    """In-memory registry of immutable scenario definitions."""

    def __init__(self) -> None:
        self._scenarios: dict[str, Scenario] = {}

    def register(self, scenario: Scenario) -> None:
        if not isinstance(scenario, Scenario):
            raise TypeError("scenario must be a Scenario.")
        if scenario.scenario_id in self._scenarios:
            raise ValueError(f"scenario is already registered: {scenario.scenario_id}")
        self._scenarios[scenario.scenario_id] = scenario

    def get(self, scenario_id: str) -> Scenario | None:
        if not isinstance(scenario_id, str):
            raise TypeError("scenario_id must be a string.")
        return self._scenarios.get(scenario_id)

    def list_available(self) -> tuple[Scenario, ...]:
        return tuple(self._scenarios.values())
