from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from cognitive_sandbox.application.agent_context_builder import AgentContextBuilder
from cognitive_sandbox.application.scenario_validator import ScenarioValidator
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.bootstrap_result import BootstrapResult
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.domain.scenario import Scenario
from cognitive_sandbox.domain.scenario_content import ScenarioContent
from cognitive_sandbox.domain.world_state import WorldState
from cognitive_sandbox.domain.world_document import WorldDocument


class WorldBootstrap:
    """Create an immutable world snapshot and initial agent contexts from a scenario."""

    def __init__(
        self,
        context_builder: AgentContextBuilder | None = None,
        *,
        world_id_factory: Callable[[], str] | None = None,
        validator: ScenarioValidator | None = None,
    ) -> None:
        self._context_builder = context_builder or AgentContextBuilder()
        self._world_id_factory = world_id_factory or (lambda: f"world_{uuid4().hex}")
        self._validator = validator or ScenarioValidator()

    def create(self, scenario: Scenario) -> BootstrapResult:
        if not isinstance(scenario, Scenario):
            raise TypeError("scenario must be a Scenario.")
        validation = self._validator.validate(scenario)
        if not validation.valid:
            raise ValueError("scenario validation failed: " + "; ".join(validation.errors))

        world_id = self._world_id_factory()
        if not isinstance(world_id, str) or not world_id.strip():
            raise ValueError("world_id_factory must return a non-empty string.")
        world_state = WorldState(
            world_id=world_id,
            name=scenario.name,
            description=scenario.description,
            state=scenario.initial_world_state,
        )

        contexts: list[AgentContext] = []
        for template in scenario.character_templates:
            character = CharacterState(
                character_id=template.get("id", template.get("character_id")),
                name=template["name"],
                role=template["role"],
                traits=tuple(template.get("traits", ())),
                goals=tuple(template.get("goals", ())),
                fears=tuple(template.get("fears", ())),
                memories=tuple(template.get("memories", ())),
            )
            contexts.append(
                self._context_builder.build(
                    character,
                    memories=(),
                    relationships=(),
                    world_state=world_state.state,
                )
            )
        return BootstrapResult(world_state=world_state, agent_contexts=tuple(contexts))

    def create_world_from_document(
        self,
        document: WorldDocument,
        initial_state,
    ) -> WorldState:
        """Create only the world snapshot portion of a content-backed runtime."""
        if not isinstance(document, WorldDocument):
            raise TypeError("document must be a WorldDocument.")
        return WorldState(
            world_id=document.world_id,
            name=document.name,
            description=document.description,
            history=document.history,
            rules=document.rules,
            state=initial_state,
        )

    def create_from_content(self, content: ScenarioContent):
        """Delegate content validation and assembly to the runtime builder."""
        from cognitive_sandbox.application.scenario_runtime_builder import ScenarioRuntimeBuilder

        return ScenarioRuntimeBuilder(world_bootstrap=self).build(content)
