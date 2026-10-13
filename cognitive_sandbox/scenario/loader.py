from __future__ import annotations

from cognitive_sandbox.application.scenario_package_loader import ScenarioPackageLoader
from cognitive_sandbox.application.scenario_runtime_builder import ScenarioRuntimeBuilder
from cognitive_sandbox.domain.scenario_runtime import ScenarioRuntime


class ScenarioRuntimeLoader:
    """Translate validated package content into the stable runtime contract."""

    def __init__(self, package_loader=None, runtime_builder=None):
        self.package_loader = package_loader or ScenarioPackageLoader()
        self.runtime_builder = runtime_builder or ScenarioRuntimeBuilder()

    def load(self, package_path) -> ScenarioRuntime:
        content = self.package_loader.load(package_path)
        return self.runtime_builder.build(content)

    def load_content(self, content) -> ScenarioRuntime:
        return self.runtime_builder.build(content)

    def load_scenario(self, scenario) -> ScenarioRuntime:
        """Adapt an in-memory legacy scenario into the shared runtime contract."""
        return self.runtime_builder.build_scenario(scenario)
