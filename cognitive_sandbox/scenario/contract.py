from __future__ import annotations

from typing import Protocol, runtime_checkable

from cognitive_sandbox.domain.scenario_runtime import ScenarioRuntime


@runtime_checkable
class ScenarioRuntimeContract(Protocol):
    """Read-only data contract consumed by runtime services."""

    scenario_id: str
    version: str
    metadata: object
    entities: tuple
    rules: tuple
    assets: object
    configuration: object
    character_cards: tuple
    world_document: object
    cognitive_rules: tuple


@runtime_checkable
class RuntimeLoader(Protocol):
    def load(self, scenario_id: str) -> ScenarioRuntime | None: ...
