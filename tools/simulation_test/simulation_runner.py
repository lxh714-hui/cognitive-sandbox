from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from types import SimpleNamespace
from types import MappingProxyType

from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.knowledge.retrieval.knowledge_query import KnowledgeQuery
from cognitive_sandbox.narrative.event_planner import EventPlanner
from tools.simulation_test.simulation_metrics import SimulationMetrics
from tools.simulation_test.simulation_report import (
    CharacterSimulationSummary, NarrativeThreadSummary, SimulationReport, ThreadStateChange,
)
from cognitive_sandbox.world_evolution.state_change import StateChange


class SimulationRunner:
    """Advance an isolated roleplay runtime using its existing clock and event pipeline.

    ``world_instance`` is the lobby metadata object. Since it contains identity only,
    callers also provide the runtime ``session`` created for that instance.
    Passing a session as the first argument is supported for small probes.
    """

    def run(self, world_instance, *, tick_count: int, random_seed: int = 0,
            enable_player_idle: bool = True, session=None, on_start=None):
        if isinstance(tick_count, bool) or not isinstance(tick_count, int) or tick_count < 0:
            raise ValueError("tick_count must be a non-negative integer.")
        if isinstance(random_seed, bool) or not isinstance(random_seed, int):
            raise ValueError("random_seed must be an integer.")
        if not isinstance(enable_player_idle, bool):
            raise TypeError("enable_player_idle must be a bool.")
        session = session or (world_instance if hasattr(world_instance, "executor") else None)
        if session is None:
            raise ValueError("A runtime session is required; WorldInstance stores lobby metadata only.")
        instance_id = getattr(world_instance, "instance_id", None) or session.world_instance_id
        if not isinstance(instance_id, str) or not instance_id:
            raise ValueError("world instance ID is unavailable.")
        if getattr(session, "world_instance_id", instance_id) != instance_id:
            raise ValueError("runtime session does not belong to the supplied WorldInstance.")
        executor = session.executor
        clock = executor.world_clock
        if clock is None or executor.event_pipeline is None:
            raise ValueError("session must provide a world clock and event pipeline.")

        start = clock.current_time()
        initial_events = {record.event_id for record in executor.event_timeline.events}
        start_threads = _threads(session)
        start_emotions = tuple(executor.emotion_engine.history) if executor.emotion_engine else ()
        start_thoughts = _thoughts(executor.cognitive_engine)
        start_relationships = tuple(executor.relationship_manager.relationships)
        start_goals = {goal.goal_id: goal for goal in executor.goal_manager.goals}
        development_engine = getattr(session, "development_engine", None)
        start_development_records = {
            cid: len(state.records) for cid, state in development_engine.states.items()
        } if development_engine is not None else {}
        lifecycle = getattr(session, "goal_lifecycle_manager", None)
        conflict_manager = getattr(session, "conflict_manager", None)
        start_transformed_conflicts = getattr(conflict_manager, "transformed_count", 0) if conflict_manager else 0
        start_goal_transitions = len(lifecycle.transitions) if lifecycle is not None else 0
        relationship_lifecycle = getattr(session, "relationship_lifecycle_manager", None)
        start_relationship_transitions = len(relationship_lifecycle.transitions) if relationship_lifecycle is not None else 0
        encounter_manager = getattr(session, "encounter_manager", None)
        start_encounter_candidates = len(encounter_manager.candidates) if encounter_manager is not None else 0
        start_encounters = len(encounter_manager.history) if encounter_manager is not None else 0
        start_evolution_changes = tuple(executor.world_evolution_engine.state_changes) if executor.world_evolution_engine else ()
        initial_world_state = _freeze_state(session.world_state)
        ctx = SimpleNamespace(
            world_clock=clock,
            world_state=session.world_state,
            agent_contexts=session.agent_contexts,
            character_minds=executor.character_minds,
            knowledge_retriever=executor.knowledge_retriever,
            knowledge_store=executor.knowledge_store,
            relationship_manager=executor.relationship_manager,
            event_timeline=executor.event_timeline,
            presence_manager=executor.presence_manager,
            goal_manager=executor.goal_manager,
            motivation_manager=executor.motivation_manager,
            narrative_pressure=session.narrative_pressure,
            emotion_engine=executor.emotion_engine,
            cognitive_engine=executor.cognitive_engine,
            resource_manager=executor.resource_manager,
            location_manager=executor.location_manager,
            encounter_manager=encounter_manager,
            conflict_manager=conflict_manager,
        )
        if on_start is not None:
            if not callable(on_start):
                raise TypeError("on_start must be callable when provided.")
            on_start(session, ctx)

        # No random choices exist in the current deterministic scheduler. The seed
        # is recorded so later stochastic policies can preserve reproducibility.
        for index in range(1, tick_count + 1):
            now = clock.advance(delta=timedelta(days=1))
            tick = WorldEvent(
                event_id=f"sim_{random_seed}_{instance_id}_{len(initial_events) + index}",
                branch_id="main", world_id=executor.world_id, event_type="world_tick",
                actor_id="system",
                payload={"elapsed_minutes": 1440, "player_idle": enable_player_idle,
                         "simulation_tick": index},
                world_revision=index, timestamp=now.isoformat(),
            )
            executor.event_pipeline.publish(tick, context=ctx)
            self._record_character_cognition(session, tick)

        new_records = tuple(record for record in executor.event_timeline.events
                            if record.event_id not in initial_events)
        state_changes = (
            tuple(executor.world_evolution_engine.state_changes)[len(start_evolution_changes):]
            if executor.world_evolution_engine else ()
        )
        emotion_history = tuple(executor.emotion_engine.history) if executor.emotion_engine else ()
        emotion_changes = tuple(item for item in emotion_history if item not in start_emotions)
        thoughts = _thoughts(executor.cognitive_engine)
        cognition_changes = tuple(item for item in thoughts if item not in start_thoughts)
        goals = {goal.goal_id: goal for goal in executor.goal_manager.goals}
        changed_goals_by_owner = {
            cid: tuple(
                f"{goal_id}: " + (
                    f"{start_goals[goal_id].progress:.2f}→{current.progress:.2f}, "
                    f"{start_goals[goal_id].status}→{current.status}"
                    if goal_id in start_goals else f"created active at {current.progress:.2f}"
                )
                for goal_id, current in goals.items()
                if current.owner_id == cid and (
                    (goal_id in start_goals and current != start_goals[goal_id]) or goal_id not in start_goals
                )
            )
            for cid in goals_by_owner(goals)
        }
        relationships = tuple(executor.relationship_manager.relationships)
        relationship_changes = tuple(item for item in relationships if item not in start_relationships)
        counts = defaultdict(int)
        for record in new_records:
            if record.event_type.startswith("npc_"):
                for actor_id in record.actor_ids:
                    counts[actor_id] += 1
        by_character = {}
        from cognitive_sandbox.application.character_state_summary import CharacterStateSummaryBuilder
        summary_builder = CharacterStateSummaryBuilder()
        for context in session.agent_contexts:
            cid = context.character_id
            emotion = executor.emotion_engine.states.get(cid) if executor.emotion_engine else None
            cognition = executor.cognitive_engine.context_for(cid) if executor.cognitive_engine else None
            visible_information = (executor.knowledge_retriever.retrieve(cid, KnowledgeQuery(limit=1000))
                                  if executor.knowledge_retriever else ())
            thoughts_for_character = tuple(getattr(executor.cognitive_engine, "thoughts", {}).get(cid, ()))
            state_summary = summary_builder.build(
                cid, goals=tuple(goals.values()), emotion=emotion, cognition=cognition,
                relationships=relationships, information=visible_information,
                recent_thoughts=thoughts_for_character,
                goal_lifecycle=lifecycle, narrative_pressure=session.narrative_pressure,
                conflicts=conflict_manager.active_conflicts if conflict_manager else (),
            )
            active_goal = next((item for item in sorted(
                (goal for goal in goals.values() if goal.owner_id == cid and goal.status == "active"),
                key=lambda goal: (-goal.priority, -goal.progress, goal.goal_id),
            )), None)
            lifecycle_goal = lifecycle.state_for(active_goal.goal_id) if active_goal is not None and lifecycle else None
            by_character[cid] = CharacterSimulationSummary(
                cid, counts[cid], changed_goals_by_owner.get(cid, ()),
                tuple(item for item in emotion_changes if item.character_id == cid),
                tuple(item for item in relationship_changes
                      if getattr(item, "source_id", None) == cid or getattr(item, "target_id", None) == cid),
                tuple(item for item in cognition_changes if item.character_id == cid),
                tuple(development_engine.get(cid).records[start_development_records.get(cid, 0):])
                if development_engine is not None else (),
                state_summary,
                getattr(lifecycle_goal, "progress_velocity", 0.0),
                getattr(lifecycle_goal, "stagnation_level", 0.0),
                getattr(lifecycle_goal, "frustration_level", 0.0),
            )
        end_threads = _threads(session)
        thread_changes = _thread_changes(start_threads, end_threads)
        thread_states = tuple(NarrativeThreadSummary(
            item.id, item.title, item.status.value, item.progress, item.pressure, item.participants, item.conflict,
        ) for item in end_threads.values())
        candidates = _candidate_snapshot(session)
        director_constraints = tuple(getattr(session, "director_constraints", ()))
        leaks = _knowledge_leaks(executor.knowledge_retriever, tuple(by_character))
        npc_count = sum(cid != session.player_id for cid in by_character)
        metrics = SimulationMetrics.calculate(
            tick_count=tick_count, events=new_records, npc_count=npc_count,
            emotion_changes=len(emotion_changes), knowledge_leaks=leaks,
            thread_changes=thread_changes,
            relationship_changes=relationship_changes,
            goal_transitions=(tuple(lifecycle.transitions)[start_goal_transitions:]
                              if lifecycle is not None else ()),
            conflicts=conflict_manager.conflicts if conflict_manager else (),
            transformed_conflicts=(getattr(conflict_manager, "transformed_count", 0) - start_transformed_conflicts
                                  if conflict_manager else 0),
        )
        # Include only changed world variables; deeper world evolution is reported
        # through the existing StateChange records from the event pipeline.
        for key in sorted(set(initial_world_state) | set(session.world_state)):
            current_world_state = _freeze_state(session.world_state)
            old, new = initial_world_state.get(key), current_world_state.get(key)
            if old != new:
                state_changes += (StateChange(
                    target_type="world", target_id=instance_id, field=key,
                    old_value=old, new_value=new, reason="world variable changed during simulation",
                    timestamp=clock.current_time().isoformat(),
                ),)
        end = clock.current_time()
        return SimulationReport(
            instance_id, getattr(world_instance, "name", getattr(session.scenario, "name", "World")),
            tick_count, start.isoformat(), end.isoformat(), (end - start).total_seconds(),
            new_records, state_changes, by_character, thread_states, thread_changes,
            director_constraints, candidates, metrics,
            random_seed, enable_player_idle,
            tuple(lifecycle.transitions)[start_goal_transitions:] if lifecycle is not None else (),
            tuple(relationship_lifecycle.transitions)[start_relationship_transitions:]
            if relationship_lifecycle is not None else (),
            relationship_lifecycle.stages if relationship_lifecycle is not None else (),
            tuple(encounter_manager.candidates[start_encounter_candidates:]) if encounter_manager is not None else (),
            tuple(encounter_manager.history[start_encounters:]) if encounter_manager is not None else (),
            session.narrative_pressure,
            tuple(conflict_manager.conflicts) if conflict_manager is not None else (),
        )

    @staticmethod
    def _record_character_cognition(session, world_tick):
        """Run cognition against each character's own scoped retrieval only."""
        executor = session.executor
        engine, retriever = executor.cognitive_engine, executor.knowledge_retriever
        if engine is None or retriever is None:
            return
        for context in session.agent_contexts:
            records = retriever.retrieve(context.character_id, KnowledgeQuery(limit=10000))
            visible = tuple(record.known_content for record in records if record.known_content.strip())
            if visible:
                engine.interpret_event(context.character_id, world_tick, visible)


def _threads(session):
    state = getattr(session, "narrative_state", None)
    return {item.id: item for item in getattr(state, "threads", ())}


def _thread_changes(before, after):
    result = []
    for thread_id, current in after.items():
        old = before.get(thread_id)
        if old is not None and (
            old.status != current.status or old.progress != current.progress
            or old.conflict != current.conflict or old.pressure != current.pressure
        ):
            result.append(ThreadStateChange(
                thread_id, current.title, old.status.value, current.status.value,
                old.progress, current.progress, old.conflict, current.conflict,
                old.pressure, current.pressure,
            ))
    return tuple(result)


def _thoughts(engine):
    if engine is None:
        return ()
    return tuple(item for character_id in sorted(engine.thoughts)
                 for item in engine.thoughts[character_id])


def _knowledge_leaks(retriever, character_ids):
    if retriever is None:
        return 0
    leaks = 0
    for character_id in character_ids:
        try:
            records = retriever.retrieve(character_id, KnowledgeQuery(limit=10000))
        except Exception:
            leaks += 1
            continue
        leaks += sum(record.owner_id != character_id and not record.visibility.allows(character_id, record.owner_id)
                     for record in records)
    return leaks


def _candidate_snapshot(session):
    from cognitive_sandbox.narrative.event_planner import EventPlanner

    executor = session.executor
    if executor.goal_manager is None or executor.presence_manager is None:
        return tuple(getattr(session, "candidate_events", ()))
    planned = EventPlanner().plan_from_state(
        executor.goal_manager.goals,
        executor.motivation_manager.motivations if executor.motivation_manager else (),
        executor.resource_manager.resources if executor.resource_manager else (),
        world_state=session.world_state,
        presence=executor.presence_manager.presences,
        locations=executor.location_manager.locations if executor.location_manager else (),
        current_time=executor.world_clock.current_time().isoformat() if executor.world_clock else None,
        pressure=session.narrative_pressure,
    )
    recorded = tuple(getattr(session, "candidate_events", ()))
    unique = {getattr(item, "candidate_id", repr(item)): item for item in (*recorded, *planned)}
    return tuple(unique[key] for key in sorted(unique))


def _freeze_state(value):
    from collections.abc import Mapping

    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_state(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_state(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_state(item) for item in value)
    return value


def goals_by_owner(goals):
    return {goal.owner_id for goal in goals.values()}
