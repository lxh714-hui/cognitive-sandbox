from __future__ import annotations

from cognitive_sandbox.application.scenario_catalog import scenario_package_directories
from cognitive_sandbox.application.scenario_package_loader import ScenarioPackageLoader
from cognitive_sandbox.application.scenario_registry import ScenarioRegistry
from cognitive_sandbox.domain.scenario import Scenario
from cognitive_sandbox.domain.scenario_content import ScenarioContent


class ScenarioLoader:
    """Discover and load scenario packages from a data directory."""

    def __init__(self, registry: ScenarioRegistry | None = None, *, package_root=None) -> None:
        self.registry = registry or ScenarioRegistry()
        self._contents: dict[str, ScenarioContent] = {}
        if registry is None:
            for package_path in scenario_package_directories(package_root):
                self.register_package(package_path)

    def register_package(self, package_path) -> ScenarioContent:
        """Load and register one package using the same path as directory discovery."""
        content = ScenarioPackageLoader().load(package_path)
        self.register_content(content)
        return content

    def register_content(self, content: ScenarioContent) -> None:
        if not isinstance(content, ScenarioContent):
            raise TypeError("content must be a ScenarioContent.")
        scenario_id = content.scenario.scenario_id
        if self.registry.get(scenario_id) is not None:
            raise ValueError(f"scenario ID is already registered: {scenario_id}")
        self.registry.register(content.scenario)
        self._contents[scenario_id] = content

    def load(self, scenario_id: str) -> Scenario | None:
        if not isinstance(scenario_id, str):
            raise TypeError("scenario_id must be a string.")
        return self.registry.get(scenario_id)

    def load_content(self, scenario_id: str) -> ScenarioContent | None:
        """Return the complete content package for scenarios backed by one."""
        if not isinstance(scenario_id, str):
            raise TypeError("scenario_id must be a string.")
        return self._contents.get(scenario_id)
