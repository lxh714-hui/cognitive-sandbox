from __future__ import annotations

import sys
from pathlib import Path

from cognitive_sandbox.application.scenario_catalog import builtin_scenarios
from cognitive_sandbox.application.scenario_package_loader import ScenarioPackageLoader
from cognitive_sandbox.application.scenario_registry import ScenarioRegistry
from cognitive_sandbox.domain.scenario import Scenario
from cognitive_sandbox.domain.scenario_content import ScenarioContent


class ScenarioLoader:
    """Load the initial built-in scenario catalog."""

    def __init__(self, registry: ScenarioRegistry | None = None) -> None:
        self.registry = registry or ScenarioRegistry()
        self._contents: dict[str, ScenarioContent] = {}
        if registry is None:
            for scenario in builtin_scenarios():
                self.registry.register(scenario)
            package_path = self._example_package_path()
            if package_path.is_dir():
                content = ScenarioPackageLoader().load(package_path)
                if self.registry.get(content.scenario.scenario_id) is not None:
                    raise ValueError(
                        f"example scenario ID is already registered: {content.scenario.scenario_id}"
                    )
                self.registry.register(content.scenario)
                self._contents[content.scenario.scenario_id] = content

    def load(self, scenario_id: str) -> Scenario | None:
        if not isinstance(scenario_id, str):
            raise TypeError("scenario_id must be a string.")
        return self.registry.get(scenario_id)

    def load_content(self, scenario_id: str) -> ScenarioContent | None:
        """Return the complete content package for scenarios backed by one."""
        if not isinstance(scenario_id, str):
            raise TypeError("scenario_id must be a string.")
        return self._contents.get(scenario_id)

    @staticmethod
    def _example_package_path() -> Path:
        bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
        return bundle_root / "assets" / "scenarios" / "example_world"
