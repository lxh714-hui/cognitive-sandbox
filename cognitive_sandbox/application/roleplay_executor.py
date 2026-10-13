from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cognitive_sandbox.application.action_dispatcher import ActionDispatcher
from cognitive_sandbox.application.actions.action_executor import ActionExecutor
from cognitive_sandbox.application.actions.action_registry import ActionHandlerRegistry
from cognitive_sandbox.application.actions.base_handler import ActionExecutionContext
from cognitive_sandbox.application.actions.observe_handler import ObserveHandler
from cognitive_sandbox.application.actions.simulation_handler import SimulationActionHandler
from cognitive_sandbox.application.actions.talk_handler import TalkHandler
from cognitive_sandbox.application.actions.wait_handler import WaitHandler
from cognitive_sandbox.application.actions.generic_action_handler import GenericActionHandler
from cognitive_sandbox.application.narrative_context import NarrativeContextBuilder
from cognitive_sandbox.application.action_semantic_mapper import ActionSemanticMapper
from cognitive_sandbox.application.npc.npc_response_service import NpcResponseService
from cognitive_sandbox.domain.action_intent import ActionIntent
from cognitive_sandbox.domain.player_action import PlayerAction
from cognitive_sandbox.domain.player_interaction import InteractionSource, PlayerInteraction
from cognitive_sandbox.domain.roleplay_result import RoleplayResult
from cognitive_sandbox.domain.roleplay_turn import RoleplayTurn
from cognitive_sandbox.domain.simulation_result import SimulationTickResult
from cognitive_sandbox.history.event_timeline import EventTimeline
from cognitive_sandbox.relationship.relationship_manager import RelationshipManager


class RoleplayExecutor:
    """Route player interactions through ActionIntent and registered handlers."""

    def __init__(
        self,
        player_action_parser,
        simulation_tick: Any,
        narrative_formatter: Any,
        dialogue_generator: Any,
        *,
        action_dispatcher: ActionDispatcher | None = None,
        action_registry: ActionHandlerRegistry | None = None,
        known_entities=(),
        known_objects=None,
        character_minds=None,
        knowledge_store=None,
        knowledge_retriever=None,
        world_id: str = "world",
        branch_id: str = "main",
        npc_response_service=None,
        event_timeline: EventTimeline | None = None,
        relationship_manager: RelationshipManager | None = None,
        event_pipeline=None,
        world_clock=None,
        time_scheduler=None,
        goal_manager=None,
        npc_scheduler=None,
        action_executor=None,
        world_evolution_engine=None,
        resource_manager=None,
        location_manager=None,
        presence_manager=None,
        motivation_manager=None,
        narrative_pressure=None,
        emotion_engine=None,
        authority_manager=None,
        cognitive_engine=None,
        scenario_config=None,
    ) -> None:
        self._parser = player_action_parser
        self.last_action_intent: ActionIntent | None = None
        self._simulation_tick = simulation_tick
        self._narrative_formatter = narrative_formatter
        self._dialogue_generator = dialogue_generator
        self._scenario_config = dict(scenario_config or {})
        self._generic_action_handler = GenericActionHandler(runtime_config=self._scenario_config)
        self.action_semantic_mapper = ActionSemanticMapper()
        self.branch_action_candidates = ()
        self.last_action_branch_mapping = None
        self._action_dispatcher = action_dispatcher or ActionDispatcher()
        self.action_executor = action_executor or ActionExecutor()
        self._known_entities = tuple(known_entities) if known_entities else None
        self._known_objects = tuple(known_objects) if known_objects is not None else None
        self._character_minds = dict(character_minds or {})
        self.knowledge_store = knowledge_store
        self.knowledge_retriever = knowledge_retriever
        self.world_id = world_id
        self.branch_id = branch_id
        self.npc_response_service = npc_response_service or NpcResponseService()
        self.event_timeline = event_timeline or EventTimeline()
        self.relationship_manager = relationship_manager or RelationshipManager(emotion_engine=emotion_engine)
        from cognitive_sandbox.event.event_pipeline import EventPipeline
        self.world_clock = world_clock
        self.time_scheduler = time_scheduler
        self.goal_manager = goal_manager
        self.npc_scheduler = npc_scheduler
        self.world_evolution_engine = world_evolution_engine
        self.resource_manager = resource_manager
        self.location_manager = location_manager
        self.presence_manager = presence_manager
        self.motivation_manager = motivation_manager
        self.narrative_pressure = narrative_pressure
        self.emotion_engine = emotion_engine
        self.authority_manager = authority_manager
        self.cognitive_engine = cognitive_engine
        self.opportunity_service = None
        self.world_tree_manager = None
        if relationship_manager is not None:
            self.relationship_manager.emotion_engine = emotion_engine
        self.event_pipeline = event_pipeline or EventPipeline(
            event_timeline=self.event_timeline,
            world_evolution_engine=self.world_evolution_engine,
            relationship_manager=self.relationship_manager,
            npc_response_service=self.npc_response_service,
            autonomous_scheduler=self.npc_scheduler,
            scheduler=self.time_scheduler,
        )
        if event_pipeline is None and self.knowledge_store is not None:
            from cognitive_sandbox.event.event_pipeline import KnowledgeEventListener
            self.event_pipeline = EventPipeline(
                event_timeline=self.event_timeline,
                world_evolution_engine=self.world_evolution_engine,
                knowledge_handler=KnowledgeEventListener(self.knowledge_store),
                relationship_manager=self.relationship_manager,
                npc_response_service=self.npc_response_service,
                autonomous_scheduler=self.npc_scheduler,
                scheduler=self.time_scheduler,
            )
        if self.emotion_engine is not None and not any(
            listener.name == "emotion" for listener in self.event_pipeline.bus.listeners
        ):
            self.event_pipeline.subscribe(self.emotion_engine, name="emotion")
        if npc_scheduler is not None and not any(
            listener.name == "autonomous_npc" for listener in self.event_pipeline.bus.listeners
        ):
            self.event_pipeline.subscribe(npc_scheduler, name="autonomous_npc")
        if event_pipeline is not None and not any(
            listener.name == "npc_response" for listener in self.event_pipeline.bus.listeners
        ):
            self.event_pipeline.subscribe(
                lambda event, context: (
                    self.npc_response_service.handle_event_with_context(event, context)
                    if context is not None and callable(getattr(self.npc_response_service, "handle_event_with_context", None))
                    else self.npc_response_service.handle_event(event, getattr(context, "agent_contexts", ()))
                ), name="npc_response"
            )
        self.action_registry = action_registry or ActionHandlerRegistry()
        if not self.action_registry.supports("observe"):
            self.action_registry.register("observe", ObserveHandler())
        if not self.action_registry.supports("look"):
            self.action_registry.register("look", self.action_registry.get("observe"))
        if not self.action_registry.supports("talk"):
            self.action_registry.register("talk", TalkHandler())
        if not self.action_registry.supports("ask"):
            self.action_registry.register("ask", self.action_registry.get("talk"))
        if not self.action_registry.supports("wait"):
            self.action_registry.register("wait", WaitHandler())
        if not self.action_registry.supports("rest"):
            self.action_registry.register("rest", self.action_registry.get("wait"))
        simulation_handler = SimulationActionHandler()
        if not self.action_registry.supports("help"):
            self.action_registry.register("help", simulation_handler)
        if not self.action_registry.supports("protect"):
            self.action_registry.register("protect", simulation_handler)

    def execute(
        self,
        turn: RoleplayTurn,
        agent_context,
        world_state: Mapping[str, Any],
        situation: str,
        target=None,
    ) -> RoleplayResult:
        """Compatibility entry point: text input becomes a TEXT interaction."""
        raw_input = turn.player_input if isinstance(turn, RoleplayTurn) else ""
        interaction = PlayerInteraction(
            actor_id=turn.player_id,
            intent="unparsed",
            source=InteractionSource.TEXT,
            raw_input=raw_input or "",
        )
        return self.execute_interaction(
            interaction, turn, agent_context, world_state, situation, target
        )

    def execute_interaction(
        self,
        interaction: PlayerInteraction,
        turn: RoleplayTurn,
        agent_context,
        world_state: Mapping[str, Any],
        situation: str,
        target=None,
        *,
        agent_contexts=(),
        scenario_content=None,
        knowledge_store=None,
        knowledge_retriever=None,
    ) -> RoleplayResult:
        if not isinstance(turn, RoleplayTurn):
            raise TypeError("turn must be a RoleplayTurn.")
        if turn.status != "executing" or turn.player_input is None:
            return self._failed(turn.turn_id)
        if interaction.actor_id != turn.player_id or turn.player_id != agent_context.character_id:
            raise ValueError("interaction, turn, and AgentContext actors must match.")
        authority_manager = self.authority_manager
        if authority_manager is None:
            from cognitive_sandbox.authority.authority_manager import AuthorityManager
            from cognitive_sandbox.authority.character_authority import CharacterAuthority
            authority_manager = AuthorityManager(
                (CharacterAuthority.player(turn.player_id), *(
                    CharacterAuthority.important_character(item.character_id)
                    for item in tuple(agent_contexts) or (agent_context,)
                    if item.character_id != turn.player_id
                )),
                player_character_id=turn.player_id,
            )
        authority_manager.require_control_permission(
                interaction.actor_id, requester_id=turn.player_id
        )
        self.authority_manager = authority_manager
        if not isinstance(world_state, Mapping):
            raise TypeError("world_state must be a mapping.")
        if interaction.source is InteractionSource.TEXT:
            action = self._parse_text(interaction.actor_id, interaction.raw_input)
            if action is None:
                return self._failed(
                    turn.turn_id,
                    "这个行动目前无法直接执行。请描述你想做什么，或者补充目标人物、地点或物品。",
                )
        else:
            action = ActionIntent(
                interaction.actor_id,
                interaction.raw_input or interaction.intent,
                interaction.intent,
                interaction.target,
                interaction.object,
                interaction.parameters,
            )
        self.last_action_intent = action
        # Convert interpreted AI/user intent into an explicit proposal record.
        # An attached World Tree can supply its existing candidate actions here;
        # material differences stay as separate proposals.
        opportunities = ()
        if self.opportunity_service is not None and action.intent != "seek_guidance":
            opportunities = self.opportunity_service.for_character(action.actor_id, limit=20)
        tree = self.world_tree_manager
        if tree is not None:
            for opportunity in opportunities:
                tree.register_opportunity(opportunity)
            existing_candidates = (*self.branch_action_candidates, *tree.candidate_actions)
        else:
            existing_candidates = self.branch_action_candidates
        self.last_action_branch_mapping = self.action_semantic_mapper.map_to_existing(
            action, existing_candidates, opportunities=opportunities
        )

        if action.intent == "seek_guidance":
            return self._guidance_result(turn.turn_id, action.actor_id)

        handler = self.action_registry.get(action.intent)
        if handler is None:
            if self._generic_action_handler.supports(action.intent):
                handler = self._generic_action_handler
            else:
                return self._failed(
                    turn.turn_id,
                    "这个行动目前无法直接执行。你可以先观察环境、前往已知地点，或尝试与附近人物交谈。",
                )
        if action.intent in {"help", "protect"}:
            decision = self._action_dispatcher.dispatch(
                action,
                known_entities=self._known_entities,
                known_objects=self._known_objects,
            )
            if not decision.accepted:
                return self._failed(turn.turn_id, decision.reason)

        contexts = tuple(agent_contexts) or (agent_context,)
        execution = ActionExecutionContext(
            turn=turn,
            agent_context=agent_context,
            agent_contexts=contexts,
            world_state=world_state,
            situation=situation,
            target=target,
            scenario_content=scenario_content,
            world_id=getattr(self, "world_id", "world"),
            branch_id=getattr(self, "branch_id", "main"),
            knowledge_store=knowledge_store or self.knowledge_store,
            knowledge_retriever=knowledge_retriever or self.knowledge_retriever,
            narrative_formatter=self._narrative_formatter,
            dialogue_service=self._dialogue_generator,
            character_minds=self._character_minds,
            simulation_tick=self._simulation_tick,
            event_timeline=self.event_timeline,
            relationship_manager=self.relationship_manager,
            event_pipeline=self.event_pipeline,
            world_clock=self.world_clock,
            time_scheduler=self.time_scheduler,
            resource_manager=self.resource_manager,
            location_manager=self.location_manager,
            presence_manager=self.presence_manager,
            motivation_manager=self.motivation_manager,
            goal_manager=self.goal_manager,
            narrative_pressure=self.narrative_pressure,
            emotion_engine=self.emotion_engine,
            authority_manager=self.authority_manager,
            cognitive_engine=self.cognitive_engine,
            narrative_context=NarrativeContextBuilder().build(
                actor_id=interaction.actor_id,
                world_state=world_state,
                clock=self.world_clock,
                timeline=self.event_timeline,
                presence_manager=self.presence_manager,
            ),
        )
        result = self.action_executor.execute(action, handler=handler, context=execution)
        mapping = self.last_action_branch_mapping
        has_world_event = bool(result.simulation_result and result.simulation_result.events)
        if result.action_executed and has_world_event:
            if tree is not None:
                tree.record_action(
                    mapping.candidate,
                    matched_candidate=mapping.matched_candidate,
                    opportunity_id=mapping.target_opportunity,
                )
            if mapping.target_opportunity and self.opportunity_service is not None:
                self.opportunity_service.resolve(mapping.target_opportunity)
        if result.action_executed and not mapping.reused_existing_branch:
            # Keep accepted proposals available for later semantic convergence at
            # this branch point; only accepted, system-executed actions are kept.
            self.branch_action_candidates = (
                *self.branch_action_candidates,
                mapping.candidate,
            )
        return self._add_npc_responses(result, execution)

    def _parse_text(self, actor_id: str, raw_input: str) -> ActionIntent | None:
        # Prefer the open-vocabulary result so natural-language parameters and
        # preferences survive the AI/fallback boundary. Keep legacy parsers as
        # compatibility fallbacks for integrations that only return PlayerAction.
        parse_open = getattr(self._parser, "interpret_action", None)
        if callable(parse_open):
            parsed = parse_open(actor_id, raw_input)
            if parsed is not None:
                if not isinstance(parsed, ActionIntent):
                    raise TypeError("interpret_action must return ActionIntent or None")
                return self._normalize_scenario_entities(parsed)
        parse_open = getattr(self._parser, "parse_action_intent", None)
        if callable(parse_open):
            parsed = parse_open(actor_id, raw_input)
            if parsed is not None:
                if not isinstance(parsed, ActionIntent):
                    raise TypeError("parse_action_intent must return ActionIntent or None")
                return self._normalize_scenario_entities(parsed)
        parse_legacy = getattr(self._parser, "parse", None)
        if callable(parse_legacy):
            legacy = parse_legacy(actor_id, raw_input)
            if isinstance(legacy, ActionIntent):
                return self._normalize_scenario_entities(legacy)
            if isinstance(legacy, PlayerAction):
                return self._normalize_scenario_entities(
                    ActionIntent(actor_id, raw_input, legacy.intent, legacy.target)
                )
            if legacy is not None:
                raise TypeError("parser must return ActionIntent, PlayerAction, or None")
        return None

    def _normalize_scenario_entities(self, action: ActionIntent) -> ActionIntent:
        aliases = {str(key).casefold(): str(value)
                   for key, value in dict(self._scenario_config.get("entity_aliases", {})).items()}
        target = aliases.get(action.target.casefold(), action.target) if action.target else None
        return action if target == action.target else ActionIntent(
            action.actor_id, action.raw_input, action.intent, target, action.object, action.parameters
        )

    def _add_npc_responses(self, result: RoleplayResult, context: ActionExecutionContext):
        simulation = result.simulation_result
        if simulation is None or not simulation.events:
            return result
        published = []
        for event in simulation.events:
            deliveries = self.event_pipeline.publish(event, context=context)
            published.extend(item for item in deliveries if item.event_id != event.event_id)
        additions = list({item.event_id: item for item in published}.values())
        if not additions:
            return result
        events = (*simulation.events, *additions)
        narratives = list(result.narrative_events)
        for event in additions:
            formatted = self._narrative_formatter.format(event)
            if formatted is not None:
                narratives.append(formatted)
        updated = SimulationTickResult(
            simulation.world_state, simulation.agent_context, events, simulation.action
        )
        return RoleplayResult(
            result.turn_id, result.action_executed, tuple(narratives),
            result.dialogue_lines, updated, result.system_message,
        )

    def _guidance_result(self, turn_id: str, character_id: str) -> RoleplayResult:
        """Offer player-visible story openings without creating an event or action."""
        opportunities = ()
        if self.opportunity_service is not None:
            opportunities = self.opportunity_service.for_character(character_id, limit=3)
        description = next((item.description for item in opportunities if item.description.strip()), None)
        if description is None:
            description = (
                "你可以先看看周围，留意眼前的人和事；也可以去熟悉的地方走走，"
                "或找一位已经认识的人聊聊。此刻没有必须完成的事。"
            )
        else:
            description = f"{description}你可以调查它，也可以暂时忽略。此刻没有必须完成的事。"
        from uuid import uuid4
        from cognitive_sandbox.domain.narrative_event import NarrativeEvent
        narrative = NarrativeEvent(f"guidance_{uuid4().hex}", "值得注意", description, ())
        return RoleplayResult(turn_id, True, (narrative,), ())

    @property
    def character_minds(self):
        return dict(self._character_minds)

    def restore_character_minds(self, character_minds) -> None:
        self._character_minds = dict(character_minds)

    @staticmethod
    def _failed(turn_id: str, system_message: str | None = None) -> RoleplayResult:
        return RoleplayResult(turn_id, False, (), (), system_message=system_message)
