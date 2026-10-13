from __future__ import annotations

from dataclasses import replace

from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.goal.goal_evaluator import GoalEvaluator
from cognitive_sandbox.event.event_lifecycle import EventLifecyclePolicy


class NpcScheduler:
    """Run eligible NPC goals once per world tick and return event candidates."""

    def __init__(self, character_minds=None, goal_manager=None, *, clock=None,
                 action_generator=None, action_executor=None, goal_evaluator=None,
                 last_tick_id: str | None = None, resource_manager=None, location_manager=None,
                 presence_manager=None, agency_manager=None, agency_evaluator=None,
                 goal_action_generator=None, routine_behaviors=(), narrative_tracker=None,
                 goal_lifecycle_manager=None, identity_manager=None, development_engine=None,
                 relationship_lifecycle_manager=None, conflict_manager=None):
        self.character_minds = dict(character_minds or {})
        self.goal_manager = goal_manager
        self.clock = clock
        self.action_generator = action_generator
        self.action_executor = action_executor
        self.goal_evaluator = goal_evaluator or GoalEvaluator()
        self.resource_manager = resource_manager
        self.location_manager = location_manager
        self.presence_manager = presence_manager
        self.agency_manager = agency_manager
        self.agency_evaluator = agency_evaluator
        self.goal_action_generator = goal_action_generator
        self.routine_behaviors = tuple(routine_behaviors)
        self.narrative_tracker = narrative_tracker
        self.goal_lifecycle_manager = goal_lifecycle_manager
        self.identity_manager = identity_manager
        self.development_engine = development_engine
        self.relationship_lifecycle_manager = relationship_lifecycle_manager
        self.conflict_manager = conflict_manager
        self.world_memory = None
        self.opportunity_service = None
        self._pending_goal_actions = {}
        self.narrative_state = None
        self.narrative_update = None
        self.last_tick_id = last_tick_id

    def bind_narrative_state(self, state, callback=None):
        self.narrative_state = state
        self.narrative_update = callback

    def handle_event(self, event: WorldEvent, context=None):
        if self.conflict_manager is not None:
            self.conflict_manager.record_event(event)
            self._sync_conflict_pressure(context)
        if event.event_type.startswith("npc_") and self.goal_lifecycle_manager is not None:
            self.goal_lifecycle_manager.evaluate(source_event_id=event.event_id, timestamp=event.timestamp or "")
            self._record_goal_outcome(event, context)
        if (event.event_type.startswith("npc_") and self.narrative_tracker is not None
                and self.narrative_state is not None):
            self.narrative_state = self.narrative_tracker.apply(self.narrative_state, event)
            if callable(self.narrative_update):
                self.narrative_update(self.narrative_state)
        if event.event_type != "world_tick" or event.event_id == self.last_tick_id:
            return ()
        self.last_tick_id = event.event_id
        if self.goal_manager is not None:
            self.goal_manager.last_evaluated_tick = event.event_id
        if self.goal_manager is None or self.action_executor is None:
            return ()
        clock = getattr(context, "world_clock", None) or self.clock
        now = clock.current_time() if clock is not None else None
        state = getattr(context, "world_state", {}) or {}
        self._refresh_conflicts(context, now)
        results = []
        for owner_id, mind in sorted(self.character_minds.items()):
            authority = getattr(self.action_executor, "authority_manager", None)
            if authority is not None and owner_id == authority.player_character_id:
                continue
            if self.presence_manager is not None:
                presence = self.presence_manager.get(owner_id)
                state_name = getattr(getattr(presence, "availability", None), "value", None)
                if state_name not in {"INTRODUCED", "ACTIVE"}:
                    continue
            goals = tuple(goal for goal in self.goal_manager.for_character(owner_id)
                          if self.goal_evaluator.is_actionable(
                              goal, world_state=state, current_time=now,
                              resource_manager=self.resource_manager,
                              location_manager=self.location_manager,
                          ))
            actions = self._agency_candidates(owner_id, goals, context, now, state) if now else ()
            if actions:
                action = actions[0].action if hasattr(actions[0], "action") else actions[0]
                action = self._attach_goal_effect(action, owner_id, goals)
                active_conflicts = self._conflicts_for(owner_id)
                if active_conflicts:
                    from cognitive_sandbox.application.npc.npc_action import NpcAction
                    parameters = dict(action.parameters)
                    parameters["conflict_response"] = tuple(item.id for item in active_conflicts)
                    strategy = _response_type_for_action(action.action_type)
                    if strategy is not None:
                        parameters["conflict_response_type"] = strategy
                    action = NpcAction(action.actor_id, action.action_type, action.target, parameters,
                                       action.reason)
                created = self.action_executor.execute(
                    action, timestamp=event.timestamp, world_revision=event.world_revision,
                    actor_name=(self.identity_manager.display_name_for(owner_id, "") if self.identity_manager else "")
                    or getattr(getattr(mind, "identity", None), "name", None),
                )
                if created is not None:
                    results.append(created)
                    goal_id = action.parameters.get("goal_id") if hasattr(action.parameters, "get") else None
                    goal = self.goal_manager.by_id(goal_id) if isinstance(goal_id, str) else None
                    if goal is None:
                        goal = max(goals, key=lambda item: (item.priority, -item.progress, item.goal_id), default=None)
                    if self.world_memory is not None:
                        parameters = getattr(action, "parameters", {})
                        conflict_context = tuple(parameters.get("conflict_response", ())) if hasattr(parameters, "get") else ()
                        self.world_memory.record_decision(
                            owner_id, action.action_type,
                            timestamp=event.timestamp or (now.isoformat() if now else None),
                            reason_context=(getattr(action, "reason", "") or
                                            ("conflicts:" + ",".join(conflict_context) if conflict_context else "goal_agency")),
                            target=getattr(action, "target", None),
                            metadata={"event_id": created.event_id, "goal_id": goal.goal_id if goal else None},
                        )
                    if goal is not None and self.goal_lifecycle_manager is not None:
                        self._pending_goal_actions[created.event_id] = (goal.goal_id, goal.progress, action.action_type)
                    if self.agency_manager is not None:
                        effectiveness = _action_effectiveness(action.action_type, ())
                        goal_effect = action.parameters.get("goal_effect", {})
                        result = goal_effect.get("result") if hasattr(goal_effect, "get") else None
                        if not isinstance(result, str):
                            result = "no_new_information" if action.action_type == "investigate" else "completed"
                        if result in {"progress", "effective", "success"}:
                            effectiveness = max(effectiveness, .7)
                        self.agency_manager.record_action(
                            owner_id, action.action_type, event.timestamp or now.isoformat(),
                            result=result, effectiveness=effectiveness,
                        )
        return tuple(results)

    def _attach_goal_effect(self, action, owner_id, goals):
        if action.action_type != "investigate" or action.parameters.get("goal_effect") is not None:
            return action
        goal_id = action.parameters.get("goal_id")
        goal = self.goal_manager.by_id(goal_id) if isinstance(goal_id, str) else None
        if goal is None:
            goal = max(goals, key=lambda item: (item.priority, -item.progress, item.goal_id), default=None)
        if goal is None:
            return action
        history = tuple(item for item in self.agency_manager.snapshot().autonomous_action_history
                        if item[0] == owner_id) if self.agency_manager is not None else ()
        last_attempt = next((item for item in reversed(history) if item[1] == "investigate"), None)
        changed_method = bool(history and last_attempt is not None and history[-1][1] != "investigate")
        result = "progress" if last_attempt is None or changed_method else "no_new_information"
        parameters = dict(action.parameters)
        parameters["goal_effect"] = {
            "result": result,
            "progress_delta": .03 if result == "progress" else 0.0,
        }
        from cognitive_sandbox.application.npc.npc_action import NpcAction
        return NpcAction(action.actor_id, action.action_type, action.target, parameters, action.reason)

    def _record_goal_outcome(self, event, context):
        pending = self._pending_goal_actions.pop(event.event_id, None)
        if pending is None:
            return
        goal_id, before_progress, action_type = pending
        goal = self.goal_manager.by_id(goal_id) if self.goal_manager is not None else None
        if goal is None:
            return
        progress_delta = max(0.0, float(goal.progress) - float(before_progress))
        params = event.payload.get("parameters", {})
        params = params if hasattr(params, "get") else {}
        effect = params.get("goal_effect", {})
        effect = effect if hasattr(effect, "get") else {}
        if event.event_type == "action_failed" or params.get("success") is False:
            result, effectiveness = "failed", 0.0
        elif progress_delta > 0:
            result, effectiveness = "progress", min(1.0, .65 + progress_delta)
        elif effect.get("result") in {"progress", "effective", "success", "failed", "no_new_information"}:
            result = effect["result"]
            effectiveness = float(effect.get("effectiveness", .25 if result in {"failed", "no_new_information"} else .7))
        else:
            result, effectiveness = "ineffective", _action_effectiveness(action_type, ())
        self.goal_lifecycle_manager.record_action_feedback(
            goal_id, action_type=action_type, timestamp=event.timestamp or "", result=result,
            effectiveness=max(0.0, min(1.0, effectiveness)), progress_delta=progress_delta,
            event_id=event.event_id,
        )
        self._refresh_goal_pressure(context)

    def _refresh_goal_pressure(self, context=None):
        if self.goal_lifecycle_manager is None:
            return
        from cognitive_sandbox.narrative.narrative_pressure import NarrativePressureCalculator
        current = self.narrative_state.pressure if self.narrative_state is not None else getattr(
            context, "narrative_pressure", None
        )
        pressure = NarrativePressureCalculator().with_goal_stagnation(
            current, self.goal_lifecycle_manager.maximum_stagnation,
        )
        if self.conflict_manager is not None:
            pressure = NarrativePressureCalculator().with_conflict_pressure(
                pressure, self.conflict_manager.pressure(),
            )
        if context is not None:
            try:
                context.narrative_pressure = pressure
            except (AttributeError, TypeError):
                pass
        if self.narrative_state is not None:
            self.narrative_state = replace(self.narrative_state, pressure=pressure)
            if callable(self.narrative_update):
                self.narrative_update(self.narrative_state)

    def _agency_candidates(self, owner_id, goals, context, now, state):
        """Use only the owner's retrieved knowledge and internal state snapshot."""
        if self.goal_action_generator is None or self.agency_manager is None or self.agency_evaluator is None:
            if self.action_generator is None:
                return ()
            return self.action_generator.generate_for(
                owner_id, goals, current_time=now, world_state=state,
                resource_manager=self.resource_manager,
            )
        from cognitive_sandbox.agency.goal_action_generator import GoalActionCandidate
        from cognitive_sandbox.knowledge.retrieval.knowledge_query import KnowledgeQuery

        retriever = getattr(context, "knowledge_retriever", None)
        relationship_manager = getattr(context, "relationship_manager", None)
        relationships = tuple(getattr(relationship_manager, "relationships", ()))
        visible = retriever.retrieve(owner_id, KnowledgeQuery(limit=1000)) if retriever is not None else ()
        emotion_engine = getattr(context, "emotion_engine", None)
        emotion = emotion_engine.states.get(owner_id) if emotion_engine is not None else None
        cognitive_engine = getattr(context, "cognitive_engine", None)
        cognition = cognitive_engine.context_for(owner_id) if cognitive_engine is not None else None
        motivation_manager = getattr(context, "motivation_manager", None)
        motivation = motivation_manager.get_for_character(owner_id, owner_id) if motivation_manager else None
        agency = self.agency_manager.get(owner_id)
        generated = []
        legacy_action_types = set()
        from cognitive_sandbox.application.npc.npc_action import NpcAction
        emergency = getattr(context, "agency_emergency_actions", {}) or {}
        emergency_action = emergency.get(owner_id) if hasattr(emergency, "get") else None
        if isinstance(emergency_action, NpcAction):
            generated.append(GoalActionCandidate(emergency_action, 1.0, "emergency", 1.0))
        current_goal = max(goals, key=lambda item: (item.priority, -item.progress, item.goal_id)) if goals else None
        if current_goal is not None:
            relationship_manager = getattr(context, "relationship_manager", None)
            relationships = relationship_manager.for_character(owner_id) if relationship_manager is not None else ()
            relationships = tuple(relationships)
            goal_candidates = self.goal_action_generator.generate(
                current_goal, visible, relationships, emotion, cognition,
                character_id=owner_id,
                current_location=getattr(self.presence_manager.get(owner_id), "current_location", None)
                if self.presence_manager else None,
                motivation=motivation,
            )
            agency_snapshot = self.agency_manager.snapshot()
            recent = tuple(item for item in agency_snapshot.autonomous_action_history if item[0] == owner_id)
            feedback = tuple(item for item in agency_snapshot.action_feedback_history if item[0] == owner_id)
            pressure = getattr(context, "narrative_pressure", None)
            goal_state = self.goal_lifecycle_manager.state_for(current_goal.goal_id) \
                if self.goal_lifecycle_manager is not None else None
            stagnation = getattr(goal_state, "stagnation_level", 0.0)
            information_need = min(1.0, len(visible) / 5.0)
            adjusted_candidates = []
            for candidate in goal_candidates:
                development_bonus = .25 * (self.development_engine.get(owner_id).tendency(
                    "behavior_tendencies", candidate.action.action_type
                ) if self.development_engine is not None else 0.0)
                relationship_bonus = (
                    self.relationship_lifecycle_manager.action_score_modifier(owner_id, candidate.action)
                    if self.relationship_lifecycle_manager is not None else 0.0
                )
                score = self.agency_evaluator.score_action(
                    candidate.score + development_bonus,
                    action_type=candidate.action.action_type,
                    recent_actions=recent,
                    feedback=feedback,
                    current_time=now,
                    current_pressure=pressure,
                    information_need=information_need if candidate.action.action_type in {"investigate", "organize", "socialize"} else 0.0,
                    goal_stagnation=stagnation,
                    emotion=emotion, cognition=cognition,
                    relationship=relationships[0] if relationships else None,
                )
                score = max(0.0, min(1.0, score + relationship_bonus))
                adjusted_candidates.append(replace(candidate, score=score))
            generated.extend(adjusted_candidates)
        generated.extend(self._conflict_agency_candidates(
            owner_id, context, now, emotion=emotion, cognition=cognition,
        ))
        # Scenario-defined deterministic actions are ranked alongside open-ended candidates.
        if self.action_generator is not None and now is not None:
            legacy = self.action_generator.generate_for(
                owner_id, goals, current_time=now, world_state=state,
                resource_manager=self.resource_manager,
            )
            from cognitive_sandbox.agency.goal_action_generator import GoalActionCandidate
            for action in legacy:
                generated.append(GoalActionCandidate(
                    action, .7, "goal", current_goal.priority if current_goal else .5,
                ))
            legacy_action_types = {item.action_type for item in legacy}
        has_visible_information = bool(visible)
        tendency = self.agency_evaluator.evaluate(
            agency, goal=current_goal, emotion=emotion, current_time=now,
            recent_actions=self.agency_manager.snapshot().autonomous_action_history,
            environment={"has_visible_information": has_visible_information}, motivation=motivation, cognition=cognition,
            current_pressure=getattr(context, "narrative_pressure", None),
            information_need=min(1.0, len(visible) / 5.0),
        )
        if self.opportunity_service is not None:
            generated.extend(self._opportunity_candidates(
                owner_id, goals, context, now, state, emotion, cognition, tendency,
            ))
        if not tendency.should_act:
            generated = [item for item in generated if item.source == "emergency"
                         or item.action.action_type in legacy_action_types]
        routine_key = f"{owner_id}:{now.date().isoformat()}"
        if not generated:
            for routine in self.routine_behaviors:
                if routine.character_id == owner_id and routine.is_due(now) and self.agency_manager.routine_count(routine_key) == 0:
                    generated.append(GoalActionCandidate(routine.candidate(), routine.priority,
                                                         "routine", routine.priority))
        if not generated:
            return ()
        timeline = tuple(getattr(getattr(context, "event_timeline", None), "events", ()))
        generated = [item for item in generated if self._lifecycle_allows(item.action, timeline, now)]
        if not generated:
            return ()
        # Emergency candidates outrank goal candidates, which outrank routines.
        rank = {"emergency": 0, "goal": 1, "routine": 2}
        generated.sort(key=lambda item: (rank.get(item.source, 3), -item.priority, -item.score,
                                         item.action.action_type))
        selected = generated[0]
        if selected.source == "routine":
            self.agency_manager.record_routine(routine_key)
        return tuple(generated)

    def _opportunity_candidates(self, owner_id, goals, context, now, state, emotion, cognition, tendency):
        """Add owner-visible possibilities to Agency ranking without forcing action."""
        from cognitive_sandbox.agency.goal_action_generator import GoalActionCandidate
        from cognitive_sandbox.application.npc.npc_action import NpcAction

        opportunities = self.opportunity_service.for_character(owner_id)
        snapshot = self.agency_manager.snapshot()
        recent = tuple(item for item in snapshot.autonomous_action_history if item[0] == owner_id)
        feedback = tuple(item for item in snapshot.action_feedback_history if item[0] == owner_id)
        stagnation = max((getattr(self.goal_lifecycle_manager.state_for(goal.goal_id), "stagnation_level", 0.0)
                          for goal in goals) if self.goal_lifecycle_manager else (), default=0.0)
        generated = []
        for opportunity in opportunities:
            source_type = getattr(opportunity.source_type, "value", opportunity.source_type)
            if source_type == "AI_PROPOSAL":
                proposed_actions = tuple(
                    item for item in getattr(opportunity, "candidate_actions", ())
                    if getattr(item, "actor_id", None) == owner_id
                )
                action_specs = tuple((item.action_type, item.target, item) for item in proposed_actions)
            else:
                action_specs = tuple((action_type, target, None)
                                     for action_type, target in _opportunity_action_types(source_type))
            for action_type, target, proposal_action in action_specs:
                params = {"opportunity_id": opportunity.opportunity_id}
                if proposal_action is not None:
                    params["proposal_action_id"] = proposal_action.action_id
                    params.update(dict(proposal_action.metadata))
                if opportunity.related_goal:
                    params["goal_id"] = opportunity.related_goal
                if opportunity.related_conflict:
                    params["conflict_response"] = (opportunity.related_conflict,)
                presence = self.presence_manager.get(owner_id) if self.presence_manager is not None else None
                location = getattr(presence, "current_location", None)
                if location:
                    params["location"] = location
                action = NpcAction(owner_id, action_type, target=target, parameters=params,
                                   reason=opportunity.description)
                score = self.agency_evaluator.score_action(
                    .22 + .18 * opportunity.importance + .08 * opportunity.urgency,
                    action_type=action_type, recent_actions=recent, feedback=feedback,
                    current_time=now, current_pressure=getattr(context, "narrative_pressure", None),
                    information_need=.7 if source_type == "INFORMATION" else 0.0,
                    goal_stagnation=stagnation,
                    emotion=emotion, cognition=cognition,
                )
                # Agency may still decline to act; this only lowers an optional candidate.
                if not tendency.should_act:
                    score *= .65
                generated.append(GoalActionCandidate(
                    action, max(0.0, min(1.0, score)), "goal",
                    # Keep an already-generated goal action ahead of optional
                    # guidance; an opportunity can lead only when no stronger
                    # ordinary candidate competes for the same decision.
                    0.0,
                ))
        return tuple(generated)

    def _conflict_agency_candidates(self, owner_id, context, now, *, emotion=None, cognition=None):
        """Expose conflict-related actions as optional Agency candidates, not score modifiers."""
        if self.conflict_manager is None:
            return ()
        from cognitive_sandbox.agency.goal_action_generator import GoalActionCandidate
        from cognitive_sandbox.application.npc.npc_action import NpcAction
        from cognitive_sandbox.conflict.conflict_context import ConflictAgencyAdapter, ConflictContext

        conflict_context = ConflictContext.for_character(owner_id, self.conflict_manager.active_conflicts)
        suggestions = ConflictAgencyAdapter().candidates_for(conflict_context)
        if not suggestions:
            return ()
        snapshot = self.agency_manager.snapshot() if self.agency_manager is not None else None
        recent = tuple(item for item in getattr(snapshot, "autonomous_action_history", ()) if item[0] == owner_id)
        feedback = tuple(item for item in getattr(snapshot, "action_feedback_history", ()) if item[0] == owner_id)
        result = []
        for suggestion in suggestions:
            pressure = suggestion.priority
            action = NpcAction(
                owner_id, suggestion.action_type, target=suggestion.target,
                parameters={"conflict_id": suggestion.conflict_id,
                            "conflict_response": (suggestion.conflict_id,)},
                reason=suggestion.reason,
            )
            score = self.agency_evaluator.score_action(
                .28 + .32 * pressure, action_type=action.action_type,
                recent_actions=recent, feedback=feedback, current_time=now,
                current_pressure=getattr(context, "narrative_pressure", None),
                emotion=emotion, cognition=cognition,
            ) if self.agency_evaluator is not None else .28 + .32 * pressure
            result.append(GoalActionCandidate(action, max(0.0, min(1.0, score)), "goal", 0.0))
        return tuple(result)

    def _conflicts_for(self, owner_id):
        if self.conflict_manager is None:
            return ()
        return tuple(item for item in self.conflict_manager.active_conflicts
                     if owner_id in item.participants)

    def _refresh_conflicts(self, context=None, now=None):
        if self.conflict_manager is None:
            return
        context = context or object()
        retriever = getattr(context, "knowledge_retriever", None)
        relationship_manager = getattr(context, "relationship_manager", None)
        relationships = tuple(getattr(relationship_manager, "relationships", ()))
        knowledge_by_character = {}
        cognition_by_character = {}
        for character_id in sorted(self.character_minds):
            if retriever is not None:
                from cognitive_sandbox.knowledge.retrieval.knowledge_query import KnowledgeQuery
                knowledge_by_character[character_id] = retriever.retrieve(character_id, KnowledgeQuery(limit=1000))
            engine = getattr(context, "cognitive_engine", None)
            if engine is not None:
                cognition_by_character[character_id] = engine.context_for(character_id)
        self.conflict_manager.refresh(
            goals=tuple(getattr(self.goal_manager, "goals", ())),
            motivations=tuple(getattr(getattr(context, "motivation_manager", None), "motivations", ())),
            resources=tuple(getattr(self.resource_manager, "resources", ())),
            knowledge_by_character=knowledge_by_character,
            cognition_by_character=cognition_by_character,
            goal_pressures=self.conflict_manager.goal_pressures(self.goal_lifecycle_manager),
            relationships=relationships,
            current_time=now,
        )
        emotion_engine = getattr(context, "emotion_engine", None)
        emotions = getattr(emotion_engine, "states", {}) if emotion_engine is not None else {}
        goals_by_id = {item.goal_id: item for item in getattr(self.goal_manager, "goals", ())}
        lifecycle = self.goal_lifecycle_manager
        for conflict in self.conflict_manager.active_conflicts:
            if getattr(conflict.status, "value", conflict.status) == "emerging" and conflict.evolution_count == 0:
                continue
            importance = max((getattr(goals_by_id.get(goal_id), "priority", 0.0)
                              for goal_id in conflict.related_goals), default=0.0)
            stalled = any(
                getattr(lifecycle.state_for(goal_id), "stagnation_level", 0.0) >= .65
                for goal_id in conflict.related_goals
            ) if lifecycle is not None else False
            self.conflict_manager.evolve(
                conflict.id, current_time=now, relationships=relationships,
                emotions=emotions, goal_importance=importance, path_sufficient=not stalled,
            )
        self._sync_conflict_pressure(context)

    def _sync_conflict_pressure(self, context=None):
        if self.conflict_manager is None:
            return
        from cognitive_sandbox.narrative.narrative_pressure import NarrativePressureCalculator
        current = getattr(context, "narrative_pressure", None)
        if current is None and self.narrative_state is not None:
            current = self.narrative_state.pressure
        pressure = NarrativePressureCalculator().with_conflict_pressure(current, self.conflict_manager.pressure())
        if hasattr(context, "narrative_pressure"):
            try:
                context.narrative_pressure = pressure
            except (AttributeError, TypeError):
                pass
        if self.narrative_state is not None:
            self.narrative_state = replace(self.narrative_state, pressure=pressure)
            if callable(self.narrative_update):
                self.narrative_update(self.narrative_state)

    def _lifecycle_allows(self, action, timeline, now):
        parameters = action.parameters
        executor = getattr(self.action_executor, "npc_event_executor", None)
        event_type = executor.event_type_for(action.action_type) if executor is not None else None
        if event_type is None:
            return True
        lifecycle = parameters.get("event_lifecycle", "REPEATABLE")
        cooldown = parameters.get("cooldown_days", 0)
        # The history stores the lifecycle marker in metadata. Older records remain valid.
        return EventLifecyclePolicy.can_generate(
            lifecycle=lifecycle, event_type=event_type, actor_id=action.actor_id,
            timestamp=now.isoformat(), timeline=timeline, cooldown_days=cooldown,
            lifecycle_key=parameters.get("lifecycle_key", event_type),
        )

def _action_effectiveness(action_type, visible):
    if action_type == "investigate":
        return 0.25 if not visible else 0.4
    if action_type in {"observe", "socialize"}:
        return 0.45
    if action_type in {"work", "repair", "collect", "patrol"}:
        return 0.7
    if action_type == "organize":
        return 0.3
    return 0.5


def _response_type_for_action(action_type):
    return {
        "rest": "avoid", "travel": "avoid", "observe": "avoid",
        "ask": "negotiate", "socialize": "negotiate", "investigate": "negotiate",
        "organize": "cooperate", "work": "cooperate", "repair": "cooperate",
        "collect": "compete", "patrol": "compete", "protect": "escalate",
    }.get(str(action_type).casefold())


def _opportunity_action_types(source_type):
    return {
        "GOAL": (("investigate", None), ("socialize", None), ("observe", None)),
        "CONFLICT": (("socialize", None), ("organize", None), ("rest", None)),
        "INFORMATION": (("investigate", None), ("socialize", None)),
        "RELATIONSHIP": (("socialize", None), ("observe", None)),
        "WORLD": (("observe", None), ("socialize", None), ("travel", None)),
    }.get(source_type, ())

