from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cognitive_sandbox.application.roleplay_turn_controller import RoleplayTurnController
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.roleplay_result import RoleplayResult
from cognitive_sandbox.domain.roleplay_turn import RoleplayTurn
from cognitive_sandbox.domain.player_interaction import PlayerInteraction
from cognitive_sandbox.domain.scenario import Scenario
from cognitive_sandbox.domain.scenario_content import ScenarioContent
from cognitive_sandbox.domain.scenario_runtime import ScenarioRuntime


class RoleplaySession:
    """Manage roleplay turn state and carry successful results into later turns."""

    def __init__(
        self,
        player_id: str,
        turn_controller: RoleplayTurnController,
        executor: Any,
        agent_context: AgentContext,
        world_state: Mapping[str, Any],
        situation: str = "当前场景",
        target: AgentContext | None = None,
        *,
        scenario: Scenario | None = None,
        scenario_content: ScenarioContent | None = None,
        agent_contexts: tuple[AgentContext, ...] = (),
        world_instance_id: str | None = None,
        presence_manager=None,
        motivation_manager=None,
        narrative_state=None,
        narrative_constraints=(),
        narrative_pressure=None,
        candidate_events=(),
        emotion_engine=None,
        director_constraints=(),
        director_history=(),
        authority_manager=None,
        world_memory=None,
        scenario_runtime: ScenarioRuntime | None = None,
    ) -> None:
        if not isinstance(player_id, str) or not player_id.strip():
            raise ValueError("player_id must not be empty.")
        if not isinstance(turn_controller, RoleplayTurnController):
            raise TypeError("turn_controller must be a RoleplayTurnController.")
        if not callable(getattr(executor, "execute", None)):
            raise TypeError("executor must provide an execute method.")
        if not isinstance(agent_context, AgentContext):
            raise TypeError("agent_context must be an AgentContext.")
        if agent_context.character_id != player_id:
            raise ValueError("player_id must match agent_context.character_id.")
        if not isinstance(world_state, Mapping):
            raise TypeError("world_state must be a mapping.")
        if not isinstance(situation, str):
            raise TypeError("situation must be a string.")
        if target is not None and not isinstance(target, AgentContext):
            raise TypeError("target must be an AgentContext or None.")
        if scenario is not None and not isinstance(scenario, Scenario):
            raise TypeError("scenario must be a Scenario or None.")
        if scenario_content is not None and not isinstance(scenario_content, ScenarioContent):
            raise TypeError("scenario_content must be a ScenarioContent or None.")
        if scenario_runtime is not None and not isinstance(scenario_runtime, ScenarioRuntime):
            raise TypeError("scenario_runtime must be a ScenarioRuntime or None.")
        if world_instance_id is not None and (
            not isinstance(world_instance_id, str) or not world_instance_id.strip()
        ):
            raise ValueError("world_instance_id must be a non-empty string or None.")

        self._player_id = player_id
        self._player_character_id = player_id
        self.turn_controller = turn_controller
        self.current_turn: RoleplayTurn | None = None
        self.executor = executor
        self.agent_context = agent_context
        from cognitive_sandbox.application.mutable_snapshot import mutable_snapshot
        self.world_state = mutable_snapshot(world_state)
        self.situation = situation
        self.target = target
        self.last_result: RoleplayResult | None = None
        self.conversation_preferences: list[dict[str, str | None]] = []
        self.scenario = scenario or (scenario_content.scenario if scenario_content else None)
        self.scenario_content = scenario_content
        self.scenario_runtime = scenario_runtime
        contexts = tuple(agent_contexts) or (agent_context,)
        if any(not isinstance(context, AgentContext) for context in contexts):
            raise TypeError("agent_contexts must contain AgentContext values.")
        self.agent_contexts = contexts
        if sum(context.character_id == player_id for context in contexts) != 1:
            raise ValueError("a world session must contain exactly one Player Character.")
        if authority_manager is None:
            from cognitive_sandbox.authority.authority_manager import AuthorityManager
            from cognitive_sandbox.authority.character_authority import CharacterAuthority
            authority_manager = AuthorityManager(
                (CharacterAuthority.player(player_id), *(
                    CharacterAuthority.important_character(context.character_id)
                    for context in contexts if context.character_id != player_id
                )),
                player_character_id=player_id,
            )
        from cognitive_sandbox.authority.authority_manager import AuthorityManager
        if not isinstance(authority_manager, AuthorityManager):
            raise TypeError("authority_manager must be an AuthorityManager.")
        if authority_manager.player_character_id != player_id:
            raise ValueError("authority manager player must match the session player.")
        self.authority_manager = authority_manager
        self.world_instance_id = world_instance_id
        from cognitive_sandbox.history.world_memory import WorldMemory, WorldMemorySnapshot
        self.world_memory = (world_memory if isinstance(world_memory, WorldMemory)
                             else WorldMemory(world_memory if isinstance(world_memory, WorldMemorySnapshot) else None))
        if not self.world_memory.current_snapshot:
            self._capture_world_memory_snapshot()
        pipeline = getattr(self.executor, "event_pipeline", None)
        if pipeline is not None and callable(getattr(pipeline, "set_world_memory", None)):
            pipeline.set_world_memory(self.world_memory)
        for manager in (
            getattr(self.executor, "conflict_manager", None),
            getattr(getattr(self.executor, "opportunity_service", None), "manager", None),
            getattr(self.executor, "world_tree_manager", None),
            getattr(self.executor, "npc_scheduler", None),
        ):
            if manager is not None:
                manager.world_memory = self.world_memory
        self.pending_interaction: PlayerInteraction | None = None
        self.knowledge_store = None
        self.knowledge_retriever = None
        from cognitive_sandbox.character_presence.character_presence import CharacterPresence, PresenceState
        from cognitive_sandbox.character_presence.presence_manager import PresenceManager
        from cognitive_sandbox.motivation.motivation_manager import MotivationManager
        from cognitive_sandbox.narrative.narrative_pressure import NarrativePressure
        from cognitive_sandbox.narrative.narrative_state import NarrativeState

        if presence_manager is None:
            snapshots = []
            for context in contexts:
                if context.character_id == player_id:
                    snapshots.append(CharacterPresence(
                        context.character_id,
                        current_location=world_state.get("location") if isinstance(world_state, Mapping) and isinstance(world_state.get("location"), str) else None,
                        availability=PresenceState.ACTIVE,
                        introduction_state=PresenceState.ACTIVE,
                    ))
                else:
                    snapshots.append(CharacterPresence(context.character_id))
            presence_manager = PresenceManager(snapshots)
        else:
            missing = []
            for context in contexts:
                if presence_manager.get(context.character_id) is None:
                    if context.character_id == player_id:
                        missing.append(CharacterPresence(
                            context.character_id,
                            current_location=world_state.get("location") if isinstance(world_state, Mapping) and isinstance(world_state.get("location"), str) else None,
                            availability=PresenceState.ACTIVE,
                            introduction_state=PresenceState.ACTIVE,
                        ))
                    else:
                        missing.append(CharacterPresence(context.character_id))
            if missing:
                presence_manager = PresenceManager((*presence_manager.presences, *missing), presence_manager.entry_rules)
        if motivation_manager is None:
            motivation_manager = MotivationManager()
        if narrative_state is None:
            narrative_state = NarrativeState()
        self.presence_manager = presence_manager
        self.motivation_manager = motivation_manager
        self.narrative_state = narrative_state
        self.narrative_constraints = tuple(narrative_constraints)
        self.narrative_pressure = narrative_pressure or narrative_state.pressure or NarrativePressure()
        self.candidate_events = tuple(candidate_events) or tuple(narrative_state.candidates)
        self.emotion_engine = emotion_engine or getattr(executor, "emotion_engine", None)
        self.director_constraints = tuple(director_constraints)
        self.director_history = tuple(director_history)
        self.director_manager = None

    def start(self) -> RoleplayTurn:
        if self.current_turn is not None and self.current_turn.status != "completed":
            raise ValueError("the current roleplay turn has not completed.")
        self.current_turn = self.turn_controller.create_turn(self.player_id)
        return self.current_turn

    def switch_player_character(self, character_id: str) -> None:
        """Player identity is fixed for the lifetime of this world instance."""
        self.authority_manager.switch_player_character(character_id)

    @property
    def player_character_id(self) -> str:
        return self._player_character_id

    @property
    def player_id(self) -> str:
        return self._player_id

    def submit_input(self, text: str) -> RoleplayTurn:
        if self.current_turn is None:
            raise ValueError("start the roleplay session before submitting input.")
        self.current_turn = self.turn_controller.submit_input(self.current_turn, text)
        self.pending_interaction = PlayerInteraction(
            actor_id=self.player_id,
            intent="unparsed",
            source="TEXT",
            raw_input=text,
        )
        return self.current_turn

    def submit_interaction(self, interaction: PlayerInteraction) -> RoleplayTurn:
        if not isinstance(interaction, PlayerInteraction):
            raise TypeError("interaction must be a PlayerInteraction.")
        if interaction.actor_id != self.player_id:
            raise ValueError("interaction actor must match the session player.")
        turn = self.submit_input(interaction.raw_input or interaction.intent)
        self.pending_interaction = interaction
        return turn

    def confirm(self) -> RoleplayResult:
        if self.current_turn is None:
            raise ValueError("start the roleplay session before confirming a turn.")

        # The controller performs the input-ready transition and action parsing;
        # the executor owns the actual simulation and presentation pipeline.
        self.turn_controller.confirm_turn(self.current_turn)
        executing_turn = self.turn_controller.get_turn(self.current_turn.turn_id)
        self.current_turn = executing_turn
        interaction = self.pending_interaction
        self.pending_interaction = None
        execute_interaction = getattr(self.executor, "execute_interaction", None)
        if interaction is not None and callable(execute_interaction):
            result = execute_interaction(
                interaction,
                executing_turn,
                self.agent_context,
                self.world_state,
                self.situation,
                self.target,
                agent_contexts=self.agent_contexts,
                scenario_content=self.scenario_content,
                knowledge_store=self.knowledge_store,
                knowledge_retriever=self.knowledge_retriever,
            )
        else:
            result = self.executor.execute(
                executing_turn,
                self.agent_context,
                self.world_state,
                self.situation,
                self.target,
            )
        interpreted = getattr(self.executor, "last_action_intent", None)
        if getattr(result, "action_executed", False) and interpreted is not None:
            parameters = getattr(interpreted, "parameters", {})
            context_parts = []
            if isinstance(parameters, Mapping):
                for name in ("opportunity_id", "goal_id", "conflict_id"):
                    value = parameters.get(name)
                    if value:
                        context_parts.append(f"{name}:{value}")
            self.world_memory.record_decision(
                self.player_id,
                getattr(interpreted, "intent", "action"),
                timestamp=(getattr(result, "simulation_result", None).events[0].timestamp
                           if getattr(result, "simulation_result", None)
                           and getattr(result.simulation_result, "events", ()) else None),
                reason_context=", ".join(context_parts) or "player_choice",
                target=getattr(interpreted, "target", None),
                metadata={"turn_id": getattr(executing_turn, "turn_id", None)},
            )
        parameters = getattr(interpreted, "parameters", {})
        if isinstance(parameters, Mapping) and parameters.get("conversation_preference") == "avoid_topic":
            topic = parameters.get("topic")
            self.conversation_preferences.append({
                "actor_id": self.player_id,
                "preference": "avoid_topic",
                "topic": topic.strip() or None if isinstance(topic, str) else None,
            })
        self.current_turn = self.turn_controller.complete_turn(executing_turn)
        self.last_result = result

        simulation_result = result.simulation_result
        if simulation_result is not None:
            self.agent_context = simulation_result.agent_context
            # SimulationTickResult contains the immutable state snapshot already;
            # copy only the outer mapping to keep the session's reference private.
            self.world_state = dict(simulation_result.world_state)
            self._capture_world_memory_snapshot()
        return result

    def _capture_world_memory_snapshot(self):
        clock = getattr(self.executor, "world_clock", None)
        current_time = clock.current_time().isoformat() if clock is not None else None
        location_manager = getattr(self.executor, "location_manager", None)
        self.world_memory.set_current_snapshot({
            "world_instance_id": self.world_instance_id,
            "world_state": self.world_state,
            "agent_contexts": tuple(self.agent_contexts),
            "current_time": current_time,
            "location_id": getattr(location_manager, "current_location_id", None),
        })
