from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from cognitive_sandbox.application.action_decision import ActionDecisionEngine
from cognitive_sandbox.application.action_event_adapter import ActionEventAdapter
from cognitive_sandbox.application.action_resolver import ActionResolver
from cognitive_sandbox.application.ai_action_interpreter import AIActionInterpreter
from cognitive_sandbox.application.ai_runtime_wiring import AIRuntimeWiring
from cognitive_sandbox.application.agent_context_builder import AgentContextBuilder
from cognitive_sandbox.application.agent_state_updater import AgentStateUpdater
from cognitive_sandbox.application.dialogue_generator import DialogueGenerator
from cognitive_sandbox.application.character_dialogue_service import CharacterDialogueService
from cognitive_sandbox.application.character_mind_builder import CharacterMindBuilder
from cognitive_sandbox.application.memory_updater import MemoryUpdater
from cognitive_sandbox.application.narrative_formatter import NarrativeFormatter
from cognitive_sandbox.application.relationship_updater import RelationshipUpdater
from cognitive_sandbox.application.actions.action_executor import ActionExecutor
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
from cognitive_sandbox.knowledge.storage.knowledge_store import KnowledgeStore
from cognitive_sandbox.knowledge.retrieval.knowledge_retriever import KnowledgeRetriever
from cognitive_sandbox.time.world_clock import WorldClock, WorldClockState
from cognitive_sandbox.time.time_scheduler import TimeScheduler
from cognitive_sandbox.goal.character_goal import CharacterGoal
from cognitive_sandbox.goal.goal_manager import GoalManager
from cognitive_sandbox.npc.autonomous.npc_action_generator import NpcActionGenerator
from cognitive_sandbox.npc.autonomous.npc_action_executor import NpcActionExecutor
from cognitive_sandbox.npc.autonomous.npc_scheduler import NpcScheduler
from cognitive_sandbox.world_evolution.location_state import LocationManager, LocationState
from cognitive_sandbox.world_evolution.resource_manager import ResourceManager
from cognitive_sandbox.world_evolution.world_evolution_engine import WorldEvolutionEngine


class GameLauncher:
    """Start a roleplay session from a registered, validated scenario."""

    def __init__(
        self,
        scenario_loader: ScenarioLoader | None = None,
        world_bootstrap: WorldBootstrap | None = None,
        action_interpreter: AIActionInterpreter | None = None,
        ai_runtime_wiring: AIRuntimeWiring | None = None,
        scenario_runtime_builder: ScenarioRuntimeBuilder | None = None,
        knowledge_retriever=None,
        dialogue_adapter=None,
    ) -> None:
        self.scenario_loader = scenario_loader or ScenarioLoader()
        self.world_bootstrap = world_bootstrap or WorldBootstrap()
        self.scenario_runtime_builder = scenario_runtime_builder or ScenarioRuntimeBuilder(
            world_bootstrap=self.world_bootstrap
        )
        self.action_interpreter = action_interpreter
        self.ai_runtime_wiring = ai_runtime_wiring or AIRuntimeWiring()
        self.knowledge_retriever = knowledge_retriever
        self.dialogue_adapter = dialogue_adapter
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
            scenario=scenario, agent_contexts=bootstrap.agent_contexts,
        )
        self.current_session = session
        return session
    def start_scenario_content(self, content: ScenarioContent, *, player_character_id=None) -> RoleplaySession:
        """Start a validated content bundle; initial event cards remain unexecuted."""
        if not isinstance(content, ScenarioContent):
            raise TypeError("content must be a ScenarioContent.")
        world_instance_id = f"world_{uuid4().hex}"
        runtime_content = content
        if content.world_document is not None:
            runtime_content = replace(
                content,
                world_document=replace(content.world_document, world_id=world_instance_id),
            )
        runtime = self.scenario_runtime_builder.build(runtime_content)
        if not runtime.agent_contexts:
            raise ValueError(f"scenario has no playable characters: {content.scenario.scenario_id}")
        selected_player = player_character_id or runtime.agent_contexts[0].character_id
        player_context = next((item for item in runtime.agent_contexts
                               if item.character_id == selected_player), None)
        if player_context is None:
            raise ValueError("所选玩家角色不在当前世界中。")
        description = (
            content.world_document.description
            if content.world_document is not None
            else content.scenario.description
        )
        session = self._create_roleplay_session(
            player_context, runtime.world_state.world_id,
            runtime.world_state.state, description,
            scenario=content.scenario, scenario_content=content,
            agent_contexts=runtime.agent_contexts,
            world_instance_id=runtime.world_state.world_id,
        )
        self.current_session = session
        return session

    def start_anchor_world(self, loader=None) -> RoleplaySession:
        """Create a fresh runtime instance from the Anchor world package."""
        from dataclasses import replace
        from uuid import uuid4
        from cognitive_sandbox.application.anchor_world_loader import AnchorWorldLoader
        from cognitive_sandbox.authority.authority_level import AuthorityLevel
        from cognitive_sandbox.domain.world_document import WorldDocument
        from cognitive_sandbox.emotion.emotional_state import EmotionalState
        from cognitive_sandbox.goal.character_goal import CharacterGoal
        from cognitive_sandbox.agency.character_agency import CharacterAgency
        from cognitive_sandbox.agency.agency_state import AgencyState
        from cognitive_sandbox.knowledge.models.knowledge_record import KnowledgeRecord, KnowledgeType
        from cognitive_sandbox.knowledge.models.knowledge_source import KnowledgeSource
        from cognitive_sandbox.knowledge.models.world_fact import WorldFact
        from cognitive_sandbox.narrative.narrative_state import NarrativeState
        from cognitive_sandbox.world_evolution.location_state import LocationState

        package = (loader or AnchorWorldLoader()).load()
        instance_id = f"anchor_{uuid4().hex}"
        content = replace(
            package.scenario_content,
            world_document=replace(package.scenario_content.world_document, world_id=instance_id),
        )
        runtime = self.scenario_runtime_builder.build(content)
        player_id = "liangjing"
        contexts = tuple(profile.agent_context for profile in runtime.agents)
        player_context = next((item for item in contexts if item.character_id == player_id), None)
        if player_context is None:
            raise ValueError("Anchor package is missing its Player Character 'liangjing'.")
        locations = tuple(LocationState(
            item["location_id"], item["name"], "active", float(item.get("safety", 0)),
            item.get("power"), tuple(item.get("attributes", ())),
        ) for item in package.locations)
        state = _thaw_mapping(runtime.world_state.state)
        state["location"] = "梁景住所"
        state["visible_objects"] = ({
            "object_id": "clock", "name": "墙上的钟", "description": "指针停在12:03。",
        },)
        goals = tuple(CharacterGoal(
            character_id, card.goals[0], "investigate_anomaly" if character_id == "liuyiyi" else "observe_changes", .7 if character_id == "liuyiyi" else .55,
        ) for character_id in ("liuyiyi", "song", "pei")
            for card in content.character_cards if card.character_id == character_id and card.goals)
        agency_state = AgencyState(tuple(
            CharacterAgency(
                character_id,
                initiative=.68 if character_id == "liuyiyi" else .52,
                motivation_strength=next((goal.priority for goal in goals if goal.owner_id == character_id), .45),
                goal_focus=next((goal.priority for goal in goals if goal.owner_id == character_id), .45),
            ) for character_id in ("liuyiyi", "song", "pei")
        ))
        from cognitive_sandbox.goal.lifecycle import GoalTransitionRule
        session = self._create_roleplay_session(
            player_context, instance_id, state, content.world_document.description,
            scenario=content.scenario, scenario_content=content, agent_contexts=contexts,
            world_instance_id=instance_id,
            autonomous_state={"locations": locations, "current_location_id": "liangjing_home", "goals": goals,
                              "agency_state": agency_state,
                              "routines": package.routines,
                              "goal_transition_rules": (GoalTransitionRule(
                                  "investigate_anomaly", "progress>=0.2", "confirm_anomaly",
                                  "确认异常真实性", .82, ("anomaly_evidence",),
                              ),)},
            narrative_data={"state": package.narrative_state,
                            "motivations": package.motivations},
            emotion_data={"states": dict(package.emotion_states)},
            cognition_data={"styles": dict(package.cognitive_styles),
                            "reasoning_profiles": dict(package.reasoning_profiles),
                            "attention_profiles": dict(package.attention_profiles)},
            authority_data={"player_character_id": player_id,
                            "authorities": tuple(package.authorities.values())},
        )
        for character_id, records in package.initial_knowledge.items():
            for data in records:
                fact_id = f"anchor:{character_id}:{data['id']}"
                fact = WorldFact(fact_id, data["content"], "initial_knowledge", "day-1",
                                 (character_id,), .7)
                session.knowledge_store.add_fact(fact)
                session.knowledge_store.add_knowledge(KnowledgeRecord(
                    character_id, fact_id, KnowledgeType(data["type"]),
                    KnowledgeSource(f"source:{fact_id}", "initial_world_package", "角色初始知识"),
                    data.get("confidence", .5), "day-1", data["content"],
                ))
        # Initial event cards remain world-package background. The offline
        # long-run runner may publish them at the first simulated tick through
        # the ordinary pipeline; creating a session itself does not execute an
        # event or reveal information to every character.
        session.anchor_world_package_id = "anchor_world"
        session.anchor_locations = package.locations
        session.anchor_content_version = package.world_card.content_version
        session.anchor_started_at = session.executor.world_clock.current_time().isoformat()
        session.anchor_world_settings = {"mode": "roleplay", "natural_simulation": True}
        session.anchor_location_relations = package.location_relations
        session.anchor_routines = package.routines or {}
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
        *,
        scenario=None,
        scenario_content: ScenarioContent | None = None,
        agent_contexts=(),
        world_instance_id: str | None = None,
        knowledge_retriever=None,
        knowledge_store=None,
        autonomous_state=None,
        narrative_data=None,
        emotion_data=None,
        director_data=None,
        authority_data=None,
        cognition_data=None,
        agency_data=None,
        world_memory_data=None,
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
        known_entities = set()
        for context in agent_contexts:
            known_entities.add(context.character_id)
            character_name = getattr(context.character_state, "name", "")
            role = getattr(context.character_state, "role", "")
            if character_name:
                known_entities.add(character_name)
            if role:
                known_entities.add(role)
        if scenario_content is not None:
            for card in scenario_content.character_cards:
                known_entities.update((card.character_id, card.name))
                if card.occupation:
                    known_entities.add(card.occupation)
        character_minds = {
            card.character_id: CharacterMindBuilder().build(card)
            for card in (scenario_content.character_cards if scenario_content is not None else ())
        }
        narrative_data = narrative_data or {}
        emotion_data = emotion_data or {}
        director_data = director_data or {}
        from cognitive_sandbox.emotion.emotion_engine import EmotionEngine
        from cognitive_sandbox.emotion.emotion_rule import EmotionRule
        encounter_emotion_rule = EmotionRule(
            ("social_encounter",), (("curiosity", .05), ("surprise", .03)),
            "unexpected_social_encounter", .7, (("curiosity", .02), ("fear", .02)), "cautious",
        )
        emotion_rules = (*EmotionEngine.DEFAULT_RULES, encounter_emotion_rule)
        emotion_engine = EmotionEngine(
            emotion_data.get("states", {}),
            emotion_data.get("history", ()),
            emotion_data.get("memories", ()),
            rules=emotion_data.get("rules", emotion_rules),
        )
        from cognitive_sandbox.character_presence.character_presence import CharacterPresence, PresenceState
        from cognitive_sandbox.character_presence.presence_manager import PresenceManager
        from cognitive_sandbox.motivation.motivation_manager import MotivationManager
        from cognitive_sandbox.narrative.narrative_state import NarrativeState

        presence_by_id = {item.character_id: item for item in narrative_data.get("presence", ())}
        for context in tuple(agent_contexts):
            if context.character_id not in presence_by_id:
                place = world_state.get("location") if hasattr(world_state, "get") else None
                presence_by_id[context.character_id] = CharacterPresence(
                    context.character_id,
                    place if context.character_id == player_context.character_id and isinstance(place, str) else None,
                    PresenceState.ACTIVE if context.character_id == player_context.character_id else PresenceState.UNKNOWN,
                    PresenceState.ACTIVE if context.character_id == player_context.character_id else PresenceState.UNKNOWN,
                )
        presence_manager = PresenceManager(
            tuple(presence_by_id.values()), narrative_data.get("entry_rules", ())
        )
        motivation_manager = MotivationManager(narrative_data.get("motivations", ()))
        from cognitive_sandbox.narrative.narrative_pressure import NarrativePressure
        initial_pressure = narrative_data.get("pressure") or NarrativePressure()
        knowledge_retriever = knowledge_retriever or self.knowledge_retriever
        if knowledge_retriever is None:
            knowledge_store = knowledge_store or KnowledgeStore()
            knowledge_retriever = KnowledgeRetriever(knowledge_store)
        elif knowledge_store is None:
            knowledge_store = getattr(knowledge_retriever, "backing_store", None)

        dialogue_adapter = self.dialogue_adapter
        if dialogue_adapter is None:
            dialogue_adapter = self.ai_runtime_wiring.create_dialogue_adapter(
                knowledge_retriever
            )
        dialogue_service = CharacterDialogueService(dialogue_adapter, DialogueGenerator())
        cognition_data = cognition_data or {}
        from cognitive_sandbox.cognition import AttentionProfile, CognitiveEngine, CognitiveStyle, ReasoningProfile
        cognitive_styles = dict(cognition_data.get("styles", {}))
        reasoning_profiles = dict(cognition_data.get("reasoning_profiles", {}))
        attention_profiles = dict(cognition_data.get("attention_profiles", {}))
        for character in tuple(agent_contexts):
            style, reasoning, attention = _default_cognitive_profiles(character)
            cognitive_styles.setdefault(character.character_id, style)
            reasoning_profiles.setdefault(character.character_id, reasoning)
            attention_profiles.setdefault(character.character_id, attention)
        cognitive_engine = CognitiveEngine(
            cognitive_styles, reasoning_profiles, attention_profiles,
            cognition_data.get("beliefs", {}), cognition_data.get("memories", {}),
            cognition_data.get("thoughts", {}),
        )
        autonomous_state = autonomous_state or {}
        agency_data = agency_data or autonomous_state.get("agency_state")
        clock_state = autonomous_state.get("clock_state")
        world_clock = WorldClock(clock_state) if clock_state is not None else WorldClock()
        scheduler_state = autonomous_state.get("scheduler_state", {})
        time_scheduler = TimeScheduler(
            autonomous_state.get("pending_events", ()),
            tick_count=scheduler_state.get("tick_count", 0),
        )
        goals = tuple(autonomous_state.get("goals", ()))
        goal_manager = GoalManager(goals, last_evaluated_tick=scheduler_state.get("last_evaluated_tick"))
        from cognitive_sandbox.goal.lifecycle import GoalLifecycleManager, GoalLifecycleSnapshot
        lifecycle_snapshot = autonomous_state.get("goal_lifecycle", GoalLifecycleSnapshot())
        if not isinstance(lifecycle_snapshot, GoalLifecycleSnapshot):
            raise TypeError("goal_lifecycle must be a GoalLifecycleSnapshot.")
        goal_lifecycle_manager = GoalLifecycleManager(
            goal_manager, autonomous_state.get("goal_transition_rules", ()), lifecycle_snapshot,
        )
        from cognitive_sandbox.development import CharacterDevelopment, DevelopmentEngine
        development_engine = DevelopmentEngine(
            autonomous_state.get("development_states", ()),
            autonomous_state.get("development_processed_event_ids", ()),
        )
        if not goals:
            for context in tuple(agent_contexts):
                if context.character_id == player_context.character_id:
                    continue
                role = str(getattr(context.character_state, "role", "")).casefold()
                character_id = context.character_id.casefold()
                if any(token in role or token in character_id for token in ("doctor", "医生")):
                    _add_clinic_goal_tree(goal_manager, context.character_id)
                elif any(token in role or token in character_id for token in ("guard", "soldier", "士兵", "守卫")):
                    goal_manager.add(CharacterGoal(context.character_id, "保护并巡查所在区域", "protect_city", 0.8, ("patrol_time",)))
        for existing_goal in tuple(goal_manager.goals):
            if existing_goal.goal_type == "repair_clinic" and not existing_goal.subgoals:
                goal_manager = _upgrade_clinic_goal_tree(goal_manager, existing_goal)
        # Some legacy scenario defaults are added after manager construction.
        # Seed lifecycle snapshots for the complete initial goal set.
        goal_lifecycle_manager.goal_manager = goal_manager
        goal_lifecycle_manager.evaluate()
        resource_manager = ResourceManager(autonomous_state.get("resources", ()))
        location_manager = LocationManager(
            autonomous_state.get("locations", ()),
            current_location_id=autonomous_state.get("current_location_id"),
        )
        if not location_manager.locations:
            current_place = world_state.get("location") if hasattr(world_state, "get") else None
            if isinstance(current_place, str) and current_place.strip():
                location_manager.add(LocationState(
                    current_place, current_place,
                    safety=_safety_scale(world_state.get("safety", 0)),
                    power=world_state.get("power") if isinstance(world_state.get("power"), bool) else None,
                ))
            if any(goal.goal_type == "repair_clinic" for goal in goal_manager.goals) and location_manager.get("clinic") is None:
                location_manager.add(LocationState("clinic", "医疗站", "damaged", 0, False, ("clinic",)))
        world_evolution_engine = WorldEvolutionEngine(
            resource_manager=resource_manager,
            location_manager=location_manager,
            goal_manager=goal_manager,
            state_changes=autonomous_state.get("state_changes", ()),
            processed_event_ids=autonomous_state.get("processed_evolution_event_ids", ()),
        )
        action_executor = ActionExecutor(
            NpcActionExecutor(world_id=world_id, branch_id="main")
        )
        from cognitive_sandbox.agency import (
            AgencyEvaluator, AgencyState, AgencyStateManager, GoalActionGenerator, RoutineBehavior,
        )
        from cognitive_sandbox.agency.narrative_activity_tracker import AgencyNarrativeTracker
        if agency_data is not None and not isinstance(agency_data, AgencyState):
            raise TypeError("agency_data must be an AgencyState snapshot.")
        npc_ids = tuple(context.character_id for context in agent_contexts
                        if context.character_id != player_context.character_id)
        agency_manager = AgencyStateManager(agency_data, npc_ids)
        routines = []
        for npc_id in npc_ids:
            configured = autonomous_state.get("routines", {}).get(npc_id, {}) if hasattr(autonomous_state.get("routines", {}), "get") else {}
            activities = tuple(configured.get("activities", ()))
            role = str(getattr(character_minds.get(npc_id).identity, "role", "") if character_minds.get(npc_id) else "").casefold()
            goal_text = " ".join(goal.description for goal in goals if goal.owner_id == npc_id)
            fallback = "organize" if any(token in goal_text for token in ("调查", "线索")) else "observe" if "观察" in goal_text else "socialize"
            behavior = activities[0] if activities and activities[0] in {
                "patrol", "collect_material", "repair_clinic", "socialize", "investigate", "observe",
                "work", "rest", "travel", "organize",
            } else fallback
            weight = configured.get("weight", .25)
            routines.append(RoutineBehavior(npc_id, behavior, ("daily",), weight))
        npc_scheduler = NpcScheduler(
            character_minds, goal_manager, clock=world_clock,
            action_generator=NpcActionGenerator(),
            action_executor=action_executor,
            last_tick_id=scheduler_state.get("last_tick_id"),
            resource_manager=resource_manager,
            location_manager=location_manager,
            presence_manager=presence_manager,
            agency_manager=agency_manager,
            agency_evaluator=AgencyEvaluator(),
            goal_action_generator=GoalActionGenerator(),
            routine_behaviors=tuple(routines),
            narrative_tracker=AgencyNarrativeTracker(),
            goal_lifecycle_manager=goal_lifecycle_manager,
            development_engine=development_engine,
        )
        executor = RoleplayExecutor(
            action_interpreter,
            tick,
            NarrativeFormatter(),
            dialogue_service,
            known_entities=known_entities,
            character_minds=character_minds,
            knowledge_store=knowledge_store,
            knowledge_retriever=knowledge_retriever,
            world_id=world_id,
            branch_id="main",
            world_clock=world_clock,
            time_scheduler=time_scheduler,
            goal_manager=goal_manager,
            npc_scheduler=npc_scheduler,
            action_executor=action_executor,
            world_evolution_engine=world_evolution_engine,
            resource_manager=resource_manager,
            location_manager=location_manager,
            presence_manager=presence_manager,
            motivation_manager=motivation_manager,
            narrative_pressure=initial_pressure,
            emotion_engine=emotion_engine,
            cognitive_engine=cognitive_engine,
        )
        from cognitive_sandbox.relationship.lifecycle import (
            RelationshipLifecycleManager, RelationshipLifecycleSnapshot,
        )
        relationship_snapshot = autonomous_state.get("relationship_lifecycle", RelationshipLifecycleSnapshot())
        if not isinstance(relationship_snapshot, RelationshipLifecycleSnapshot):
            raise TypeError("relationship_lifecycle must be a RelationshipLifecycleSnapshot.")
        relationship_lifecycle_manager = RelationshipLifecycleManager(
            executor.relationship_manager,
            character_ids=tuple(context.character_id for context in agent_contexts),
            emotion_engine=emotion_engine,
            cognitive_engine=cognitive_engine,
            snapshot=relationship_snapshot,
        )
        npc_scheduler.relationship_lifecycle_manager = relationship_lifecycle_manager
        executor.event_pipeline.subscribe(relationship_lifecycle_manager, name="relationship_lifecycle")
        from cognitive_sandbox.authority.authority_manager import AuthorityManager
        from cognitive_sandbox.authority.character_authority import CharacterAuthority
        authority_data = authority_data or {}
        authorities = tuple(authority_data.get("authorities", ()))
        if authorities:
            authority_manager = AuthorityManager(
                authorities,
                player_character_id=authority_data.get("player_character_id", player_context.character_id),
            )
        else:
            authority_manager = AuthorityManager(
                (CharacterAuthority.player(player_context.character_id), *(
                    CharacterAuthority.important_character(context.character_id)
                    for context in agent_contexts if context.character_id != player_context.character_id
                )),
                player_character_id=player_context.character_id,
            )
        from cognitive_sandbox.encounter import EncounterManager, EncounterSnapshot
        encounter_snapshot = autonomous_state.get("encounters", EncounterSnapshot())
        if not isinstance(encounter_snapshot, EncounterSnapshot):
            raise TypeError("encounters must be an EncounterSnapshot.")
        encounter_manager = EncounterManager(
            authority_manager=authority_manager,
            relationship_manager=executor.relationship_manager,
            relationship_lifecycle_manager=relationship_lifecycle_manager,
            emotion_engine=emotion_engine,
            cognitive_engine=cognitive_engine,
            knowledge_retriever=knowledge_retriever,
            character_minds=character_minds,
            goal_manager=goal_manager,
            presence_manager=presence_manager,
            location_manager=location_manager,
            snapshot=encounter_snapshot,
        )
        npc_scheduler.encounter_manager = encounter_manager
        executor.event_pipeline.subscribe(encounter_manager, name="social_encounters")
        from cognitive_sandbox.information import InformationManager, InformationSnapshot
        information_snapshot = autonomous_state.get("information", InformationSnapshot())
        information_manager = InformationManager(
            knowledge_store=knowledge_store,
            knowledge_retriever=knowledge_retriever,
            authority_manager=authority_manager,
            presence_manager=presence_manager,
            relationship_manager=executor.relationship_manager,
            agency_manager=agency_manager,
            cognitive_engine=cognitive_engine,
            world_clock=world_clock,
            snapshot=information_snapshot,
        )
        executor.event_pipeline.subscribe_before(information_manager, "knowledge", name="information_propagation")
        session = RoleplaySession(
            player_id=player_context.character_id,
            turn_controller=RoleplayTurnController(),
            executor=executor,
            agent_context=player_context,
            world_state=world_state,
            situation=situation,
            scenario=scenario,
            scenario_content=scenario_content,
            agent_contexts=tuple(agent_contexts),
            world_instance_id=world_instance_id or world_id,
            presence_manager=presence_manager,
            motivation_manager=motivation_manager,
            narrative_state=narrative_data.get("state", NarrativeState()),
            narrative_constraints=narrative_data.get("constraints", ()),
            narrative_pressure=narrative_data.get("pressure"),
            candidate_events=narrative_data.get("candidates", ()),
            emotion_engine=emotion_engine,
            director_constraints=director_data.get("constraints", ()),
            director_history=director_data.get("history", ()),
            authority_manager=authority_manager,
            world_memory=world_memory_data,
        )
        executor.authority_manager = authority_manager
        action_executor.authority_manager = authority_manager
        session.encounter_manager = encounter_manager
        session.information_manager = information_manager
        session.start()
        session.knowledge_retriever = knowledge_retriever
        session.knowledge_store = knowledge_store
        from cognitive_sandbox.director.director_manager import DirectorManager
        session.director_manager = DirectorManager(
            session, constraints=director_data.get("constraints", ()),
            history=director_data.get("history", ()),
        )
        if "state" not in narrative_data:
            session.narrative_state = NarrativeState.from_snapshot(
                goals=goal_manager.goals,
                motivations=motivation_manager.motivations,
                resources=resource_manager.resources,
                world_state=world_state,
                presence=presence_manager.presences,
                locations=location_manager.locations,
                current_time=world_clock.current_time().isoformat(),
                constraints=session.narrative_constraints,
            )
            session.narrative_pressure = session.narrative_state.pressure
            session.executor.narrative_pressure = session.narrative_pressure
            session.candidate_events = session.narrative_state.candidates
        def sync_agency_narrative(updated_state):
            session.narrative_state = updated_state
            session.narrative_pressure = updated_state.pressure or session.narrative_pressure
            session.candidate_events = tuple(updated_state.candidates)
            session.executor.narrative_pressure = session.narrative_pressure
        npc_scheduler.bind_narrative_state(session.narrative_state, sync_agency_narrative)
        def add_information_pressure(clue, paths):
            if not paths:
                return
            from dataclasses import replace
            pressure = session.narrative_pressure
            if pressure is None:
                return
            increment = min(.04, .01 * len(paths))
            session.narrative_pressure = replace(
                pressure, urgency=min(1.0, pressure.urgency + increment),
                unresolved_degree=min(1.0, pressure.unresolved_degree + increment),
                trend="rising" if increment else pressure.trend,
            )
            session.narrative_state = replace(session.narrative_state, pressure=session.narrative_pressure)
            executor.narrative_pressure = session.narrative_pressure
        information_manager.bind_narrative_pressure(add_information_pressure)
        from cognitive_sandbox.conflict import ConflictManager, ConflictSnapshot
        conflict_snapshot = autonomous_state.get("conflicts", ConflictSnapshot())
        conflict_manager = ConflictManager(conflict_snapshot)
        conflict_manager.world_memory = session.world_memory
        npc_scheduler.conflict_manager = conflict_manager
        session.conflict_manager = conflict_manager
        from cognitive_sandbox.narrative.opportunity import NarrativeOpportunityService
        opportunity_service = NarrativeOpportunityService(
            world_clock=world_clock,
            goal_manager=goal_manager,
            goal_lifecycle_manager=goal_lifecycle_manager,
            conflict_manager=conflict_manager,
            location_manager=location_manager,
            information_manager=information_manager,
            relationship_lifecycle_manager=relationship_lifecycle_manager,
            world_state_provider=lambda: session.world_state,
        )
        session.opportunity_service = opportunity_service
        opportunity_service.manager.world_memory = session.world_memory
        executor.opportunity_service = opportunity_service
        npc_scheduler.opportunity_service = opportunity_service
        from cognitive_sandbox.application.world_tree_manager import WorldTreeManager
        executor.world_tree_manager = WorldTreeManager(
            world_id,
            narrative_data.get("world_tree"),
            world_memory=session.world_memory,
        )
        npc_scheduler.world_memory = session.world_memory
        saved_opportunities = tuple(narrative_data.get("opportunities", ()))
        opportunity_service.restore(saved_opportunities)
        if getattr(session.scenario, "scenario_id", None) == "anchor_world":
            from cognitive_sandbox.domain.actions import ActionCandidate
            from cognitive_sandbox.narrative.opportunity import (
                NarrativeOpportunity, OpportunitySourceType,
            )
            clock_opportunity = NarrativeOpportunity(
                "investigate_clock", OpportunitySourceType.WORLD,
                related_character=session.player_id,
                visibility="owner", importance=.75, urgency=.3,
                possible_actions=("看看钟", "检查钟表", "直接离开房间"),
                created_time=world_clock.current_time().isoformat(),
                expiry=None,
                description="墙上的钟停在12:03。这个细节仍留在你的视线里。",
                visible_character_ids=(session.player_id,),
                source="world_rule",
                source_id="anchor_world:liangjing_home:clock",
                internal_context={"location_id": "liangjing_home", "object_id": "clock"},
                related_entities=("liangjing_home", "clock"),
                candidate_actions=(ActionCandidate(
                    action_type="inspect", intent="inspect", actor_id=session.player_id,
                    target="钟", target_refs=("钟",), motivation="investigate_visible_detail",
                    metadata={"objective": "inspect:钟", "method": "inspect", "risk": .25,
                              "relationship_effect": "no_direct_change",
                              "expected_effect": "inspect_target"},
                    action_id="anchor_clock_inspection",
                ),),
            )
            if not any(item.opportunity_id == clock_opportunity.opportunity_id
                       for item in opportunity_service.snapshot()):
                opportunity_service.register(clock_opportunity)
                executor.world_tree_manager.register_opportunity(clock_opportunity)
        executor.branch_action_candidates = executor.world_tree_manager.candidate_actions
        from types import SimpleNamespace
        npc_scheduler._refresh_conflicts(
            SimpleNamespace(knowledge_retriever=knowledge_retriever,
                            cognitive_engine=cognitive_engine,
                            motivation_manager=motivation_manager,
                            relationship_manager=executor.relationship_manager,
                            emotion_engine=emotion_engine,
                            narrative_pressure=session.narrative_pressure),
            world_clock.current_time(),
        )
        session.narrative_pressure = getattr(session.narrative_state, "pressure", session.narrative_pressure)
        executor.narrative_pressure = session.narrative_pressure
        session.agency_manager = agency_manager
        session.goal_lifecycle_manager = goal_lifecycle_manager
        session.development_engine = development_engine
        session.relationship_lifecycle_manager = relationship_lifecycle_manager
        # Identity is a separate, stable-ID keyed display layer. Legacy saves
        # without snapshots receive defaults from their existing character cards.
        from cognitive_sandbox.identity import CharacterIdentity, IdentityManager
        saved_identities = tuple(autonomous_state.get("identities", ()))
        if saved_identities:
            identity_manager = IdentityManager(saved_identities)
        else:
            cards = scenario_content.character_cards if scenario_content is not None else ()
            card_by_id = {card.character_id: card for card in cards}
            identity_manager = IdentityManager(
                CharacterIdentity(
                    cid,
                    card_by_id[cid].name if cid in card_by_id else getattr(getattr(mind, "identity", None), "name", cid),
                    card_by_id[cid].name if cid in card_by_id else getattr(getattr(mind, "identity", None), "name", cid),
                    editable=card_by_id[cid].identity_editable if cid in card_by_id else True,
                    naming_source="scenario_package" if cid in card_by_id else "legacy_save",
                    public_description=card_by_id[cid].background if cid in card_by_id else "",
                ) for cid, mind in (character_minds or {ctx.character_id: None for ctx in agent_contexts}).items()
            )
        session.identity_manager = identity_manager
        npc_scheduler.identity_manager = identity_manager
        session.executor.event_pipeline.subscribe(development_engine, name="character_development")
        if autonomous_state:
            session.executor.npc_scheduler.last_tick_id = scheduler_state.get("last_tick_id")
        package_state = (autonomous_state.get("world_package", autonomous_state.get("demo", {}))
                         if hasattr(autonomous_state, "get") else {})
        session.anchor_content_version = package_state.get("content_version") or getattr(session, "anchor_content_version", None)
        session.anchor_started_at = package_state.get("started_at") or getattr(session, "anchor_started_at", None)
        session.anchor_world_settings = dict(package_state.get("settings", {}))
        session.anchor_location_relations = package_state.get("location_relations", ())
        session.anchor_routines = package_state.get("routines", {})
        if session.scenario is not None and getattr(session.scenario, "scenario_id", None) == "anchor_world":
            # Older saves predate world-package metadata; restore package defaults.
            from cognitive_sandbox.application.anchor_world_loader import AnchorWorldLoader
            anchor_package = AnchorWorldLoader().load()
            session.anchor_content_version = session.anchor_content_version or anchor_package.world_card.content_version
            session.anchor_location_relations = session.anchor_location_relations or anchor_package.location_relations
            session.anchor_routines = session.anchor_routines or anchor_package.routines
        if package_state.get("replay_index") is not None:
            session.story_replay_index = int(package_state.get("replay_index", 0))
        return session

    def restore_saved_world(self, saved_world) -> RoleplaySession:
        """Recreate runtime services around saved snapshots without bootstrapping a world."""
        from cognitive_sandbox.knowledge.retrieval.knowledge_retriever import KnowledgeRetriever
        from cognitive_sandbox.knowledge.storage.knowledge_store import KnowledgeStore

        if not isinstance(saved_world, dict):
            raise TypeError("saved_world must be a decoded save mapping.")
        metadata = saved_world.get("metadata")
        session_data = saved_world.get("session")
        knowledge = saved_world.get("knowledge", {})
        if not isinstance(session_data, dict) or not isinstance(knowledge, dict):
            raise ValueError("saved world is missing session or knowledge state.")
        agent_context = session_data.get("agent_context")
        agent_contexts = session_data.get("agent_contexts", ())
        world_state = session_data.get("world_state")
        if not agent_contexts:
            agent_contexts = (agent_context,)
        store = KnowledgeStore()
        facts = tuple(knowledge.get("facts", ()))
        records = tuple(knowledge.get("records", ()))
        for fact in facts:
            store.add_fact(fact)
        for record in records:
            store.add_knowledge(record)
        retriever = KnowledgeRetriever(store)
        session = self._create_roleplay_session(
            agent_context,
            metadata.world_id,
            world_state,
            session_data.get("situation", "当前场景"),
            scenario=session_data.get("scenario"),
            scenario_content=session_data.get("scenario_content"),
            agent_contexts=agent_contexts,
            world_instance_id=metadata.instance_id,
            knowledge_retriever=retriever,
            knowledge_store=store,
            autonomous_state=saved_world.get("autonomous", {}),
            narrative_data=saved_world.get("narrative", {}),
            emotion_data=saved_world.get("emotion", {}),
            director_data=saved_world.get("director", {}),
            authority_data=saved_world.get("authority", {}),
            cognition_data=saved_world.get("cognition", {}),
            agency_data=saved_world.get("autonomous", {}).get("agency_state"),
            world_memory_data=saved_world.get("world_memory"),
        )
        session.target = session_data.get("target")
        minds = saved_world.get("character_minds", {})
        session.executor.event_timeline.restore(saved_world.get("timeline", ()))
        session.executor.relationship_manager.restore_relationships(saved_world.get("relationships", ()))
        session.executor.relationship_manager.mark_events_processed(
            record.event_id for record in session.executor.event_timeline.events
        )
        from cognitive_sandbox.domain.character_mind import RelationshipContext

        scoped_minds = {}
        for character_id, mind in minds.items():
            relationships = session.executor.relationship_manager.for_character(character_id)
            if relationships or getattr(mind.relationship_context, "owner_id", None) is not None:
                mind = replace(
                    mind,
                    relationship_context=RelationshipContext(character_id, relationships),
                )
            scoped_minds[character_id] = mind
        minds = scoped_minds
        session.executor.restore_character_minds(minds)
        self.current_session = session
        return session


def _default_cognitive_profiles(character):
    from cognitive_sandbox.cognition import AttentionProfile, CognitiveStyle, ReasoningProfile
    role = str(getattr(character.character_state, "role", "")).casefold()
    identity = character.character_id.casefold()
    if any(word in role + identity for word in ("investig", "research", "研究", "调查")):
        return (CognitiveStyle(analytical=.8, suspicious=.7, strategic=.65),
                ReasoningProfile(.8, .65, .8, .65),
                AttentionProfile(physical_detail=.7, risk_signal=.65, temporal_pattern=.8))
    if any(word in role + identity for word in ("merchant", "商人")):
        return (CognitiveStyle(pragmatic=.8, strategic=.65),
                ReasoningProfile(.55, .45, .5, .65),
                AttentionProfile(resource_signal=.85, social_signal=.6))
    if any(word in role + identity for word in ("soldier", "guard", "police", "士兵", "守卫", "警察")):
        return (CognitiveStyle(analytical=.55, pragmatic=.7, suspicious=.6),
                ReasoningProfile(.55, .5, .6, .55),
                AttentionProfile(risk_signal=.85, physical_detail=.7))
    return CognitiveStyle(), ReasoningProfile(), AttentionProfile()


def _thaw_mapping(value):
    from collections.abc import Mapping
    if isinstance(value, Mapping):
        return {key: _thaw_mapping(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_thaw_mapping(item) for item in value)
    if isinstance(value, frozenset):
        return {_thaw_mapping(item) for item in value}
    return value


def _add_clinic_goal_tree(manager: GoalManager, owner_id: str) -> None:
    parent_id = f"{owner_id}:repair_clinic"
    materials_id = f"{owner_id}:collect_materials"
    power_id = f"{owner_id}:restore_power"
    manager.add(CharacterGoal(
        owner_id, "修复医疗站", "repair_clinic", 0.8,
        goal_id=parent_id, subgoals=(materials_id, power_id),
        completion_conditions=("all_subgoals_completed",),
    ))
    manager.add(CharacterGoal(
        owner_id, "收集医疗站修复材料", "collect_materials", 0.75,
        ("materials_needed",), goal_id=materials_id, parent_goal_id=parent_id,
    ))
    manager.add(CharacterGoal(
        owner_id, "恢复医疗站供电", "restore_power", 0.7,
        ("materials_available", "clinic_power_restored"), 0.0, "paused",
        goal_id=power_id, parent_goal_id=parent_id,
        completion_conditions=("clinic_power_restored",),
    ))


def _upgrade_clinic_goal_tree(manager: GoalManager, old_goal: CharacterGoal) -> GoalManager:
    parent_id = old_goal.goal_id
    materials_id = f"{old_goal.owner_id}:collect_materials"
    power_id = f"{old_goal.owner_id}:restore_power"
    manager.replace_goal(replace(
        old_goal, subgoals=(materials_id, power_id),
        completion_conditions=("all_subgoals_completed",),
    ))
    manager.add(CharacterGoal(
        old_goal.owner_id, "收集医疗站修复材料", "collect_materials", old_goal.priority,
        ("materials_needed",), goal_id=materials_id, parent_goal_id=parent_id,
    ))
    manager.add(CharacterGoal(
        old_goal.owner_id, "恢复医疗站供电", "restore_power", old_goal.priority,
        ("materials_available", "clinic_power_restored"), 0.0, "paused",
        goal_id=power_id, parent_goal_id=parent_id,
        completion_conditions=("clinic_power_restored",),
    ))
    return manager


def _safety_scale(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        normalized = float(value)
        if 0 <= normalized <= 1:
            normalized *= 100
        return max(0.0, min(100.0, normalized))
    return 0.0
