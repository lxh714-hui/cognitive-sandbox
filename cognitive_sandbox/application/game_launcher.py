from __future__ import annotations

from uuid import uuid4

from cognitive_sandbox.application.action_decision import ActionDecisionEngine
from cognitive_sandbox.application.action_event_adapter import ActionEventAdapter
from cognitive_sandbox.application.action_resolver import ActionResolver
from cognitive_sandbox.application.ai_action_interpreter import AIActionInterpreter
from cognitive_sandbox.application.ai_runtime_wiring import AIRuntimeWiring
from cognitive_sandbox.application.agent_context_builder import AgentContextBuilder
from cognitive_sandbox.application.agent_state_updater import AgentStateUpdater
from cognitive_sandbox.application.dialogue_generator import DialogueGenerator
from cognitive_sandbox.application.memory_updater import MemoryUpdater
from cognitive_sandbox.application.narrative_formatter import NarrativeFormatter
from cognitive_sandbox.application.relationship_updater import RelationshipUpdater
from cognitive_sandbox.application.roleplay_executor import RoleplayExecutor
from cognitive_sandbox.application.roleplay_session import RoleplaySession
from cognitive_sandbox.application.roleplay_turn_controller import RoleplayTurnController
from cognitive_sandbox.application.scenario_runtime_builder import ScenarioRuntimeBuilder
from cognitive_sandbox.application.scenario_loader import ScenarioLoader
from cognitive_sandbox.application.simulation_tick import SimulationTick
from cognitive_sandbox.application.world_bootstrap import WorldBootstrap
from cognitive_sandbox.application.world_state_applier import WorldStateApplier
from cognitive_sandbox.application.world_state_updater import WorldStateUpdater
from cognitive_sandbox.domain.scenario_content import ScenarioContent


class GameLauncher:
    """Start a roleplay session from a registered, validated scenario."""

    def __init__(
        self,
        scenario_loader: ScenarioLoader | None = None,
        world_bootstrap: WorldBootstrap | None = None,
        action_interpreter: AIActionInterpreter | None = None,
        ai_runtime_wiring: AIRuntimeWiring | None = None,
        scenario_runtime_builder: ScenarioRuntimeBuilder | None = None,
    ) -> None:
        self.scenario_loader = scenario_loader or ScenarioLoader()
        self.world_bootstrap = world_bootstrap or WorldBootstrap()
        self.scenario_runtime_builder = scenario_runtime_builder or ScenarioRuntimeBuilder(
            world_bootstrap=self.world_bootstrap
        )
        self.action_interpreter = action_interpreter
        self.ai_runtime_wiring = ai_runtime_wiring or AIRuntimeWiring()
        self.current_session: RoleplaySession | None = None

    def start_scenario(self, scenario_id: str) -> RoleplaySession:
        load_content = getattr(self.scenario_loader, "load_content", None)
        content = load_content(scenario_id) if callable(load_content) else None
        if content is not None:
            return self.start_scenario_content(content)

        scenario = self.scenario_loader.load(scenario_id)
        if scenario is None:
            raise ValueError(f"unknown scenario: {scenario_id}")

        bootstrap = self.world_bootstrap.create(scenario)
        if not bootstrap.agent_contexts:
            raise ValueError(f"scenario has no playable characters: {scenario_id}")
        session = self._create_roleplay_session(
            bootstrap.agent_contexts[0], bootstrap.world_state.world_id,
            bootstrap.world_state.state, scenario.description,
        )
        self.current_session = session
        return session

    def start_scenario_content(self, content: ScenarioContent) -> RoleplaySession:
        """Start a validated content bundle; initial event cards remain unexecuted."""
        if not isinstance(content, ScenarioContent):
            raise TypeError("content must be a ScenarioContent.")
        runtime = self.scenario_runtime_builder.build(content)
        if not runtime.agent_contexts:
            raise ValueError(f"scenario has no playable characters: {content.scenario.scenario_id}")
        description = (
            content.world_document.description
            if content.world_document is not None
            else content.scenario.description
        )
        session = self._create_roleplay_session(
            runtime.agent_contexts[0], runtime.world_state.world_id,
            runtime.world_state.state, description,
        )
        self.current_session = session
        return session

    def create_world_creation_session(self, generator=None):
        """Create the generation-and-confirmation application session."""
        if generator is None:
            from cognitive_sandbox.application.llm_provider import LLMProvider
            from cognitive_sandbox.application.world_generator import WorldGenerator

            generator = WorldGenerator(LLMProvider(self.ai_runtime_wiring.load_config()))
        from cognitive_sandbox.application.world_creation_session import WorldCreationSession

        return WorldCreationSession(generator, self)

    def _create_roleplay_session(
        self,
        player_context,
        world_id: str,
        world_state,
        situation: str,
    ) -> RoleplaySession:
        tick = SimulationTick(
            ActionDecisionEngine(),
            ActionResolver(),
            ActionEventAdapter(
                world_id=world_id,
                branch_id="main",
                world_revision=1,
                event_id_factory=lambda: f"event_{uuid4().hex}",
            ),
            WorldStateUpdater(),
            WorldStateApplier(),
            MemoryUpdater(),
            RelationshipUpdater(),
            AgentStateUpdater(),
            AgentContextBuilder(),
        )
        action_interpreter = self.action_interpreter or self.ai_runtime_wiring.create_action_interpreter()
        executor = RoleplayExecutor(action_interpreter, tick, NarrativeFormatter(), DialogueGenerator())
        session = RoleplaySession(
            player_id=player_context.character_id,
            turn_controller=RoleplayTurnController(),
            executor=executor,
            agent_context=player_context,
            world_state=world_state,
            situation=situation,
        )
        session.start()
        return session
