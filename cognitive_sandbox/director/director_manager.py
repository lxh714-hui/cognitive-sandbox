from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from cognitive_sandbox.narrative.event_planner import EventPlanner
from cognitive_sandbox.narrative.narrative_state import NarrativeState

from .constraint_evaluator import DirectorConstraintEvaluator
from .director_constraint import DirectorConstraint, DirectorConstraintStatus
from .director_intent import DirectorIntent, DirectorIntentParser
from .director_path_finder import DirectorPathFinder
from .director_result import DirectorResult


class DirectorManager:
    """Turn player preferences into soft narrative constraints and planner candidates."""

    def __init__(self, session, *, evaluator=None, path_finder=None, parser=None, planner=None,
                 constraints=(), history=(), id_factory=None):
        self.session = session
        self.evaluator = evaluator or DirectorConstraintEvaluator()
        self.path_finder = path_finder or DirectorPathFinder()
        self.parser = parser or DirectorIntentParser()
        self.planner = planner or EventPlanner()
        self._id_factory = id_factory or (lambda: uuid4().hex)
        self.constraints = list(constraints)
        self.history = list(history)
        self._sync_session()

    def submit_text(self, text: str) -> DirectorResult:
        known = tuple((item.character_id, item.character_state.name)
                      for item in getattr(self.session, "agent_contexts", ()))
        return self.submit_intent(self.parser.parse(text, known))

    def submit_intent(self, intent: DirectorIntent) -> DirectorResult:
        if not isinstance(intent, DirectorIntent):
            raise TypeError("intent must be DirectorIntent.")
        authority_manager = getattr(self.session, "authority_manager", None)
        if authority_manager is not None:
            authority_manager.require_director_permission("create_constraint")
        constraint = DirectorConstraint(
            f"director:{self._id_factory()}", intent, intent.target, intent.priority,
            ("respect_presence", "respect_character_goals", "respect_relationships_and_emotions"),
            constraint_type=intent.constraint_type, target_kind=intent.constraint_target,
            category=intent.category, source="player", strength=intent.strength,
        )
        presence_manager = getattr(self.session, "presence_manager", None)
        presences = tuple(getattr(presence_manager, "presences", ()))
        world_state = getattr(self.session, "world_state", {})
        constraint, reason = self.evaluator.evaluate(
            constraint, presences=presences,
            current_location=world_state.get("location") if hasattr(world_state, "get") else None,
        )
        if constraint.status is DirectorConstraintStatus.BLOCKED:
            result = DirectorResult(intent, constraint, False, reason)
            self.constraints.append(constraint)
            self.history.append(result)
            self._sync_session()
            return result

        state = getattr(self.session, "narrative_state", NarrativeState())
        executor = getattr(self.session, "executor", None)
        goals = tuple(getattr(getattr(executor, "goal_manager", None), "goals", ()))
        resources = tuple(getattr(getattr(executor, "resource_manager", None), "resources", ()))
        locations = tuple(getattr(getattr(executor, "location_manager", None), "locations", ()))
        clock = getattr(executor, "world_clock", None)
        current_time = clock.current_time().isoformat() if clock is not None else None
        # Director planning gets only public, presentation-safe world fields and
        # public motivation projections. It never receives KnowledgeStore data,
        # hidden motives, or the complete runtime state.
        public_world_state = self._public_world_state(world_state)
        motivation_manager = getattr(self.session, "motivation_manager", None)
        motivations = tuple(
            view for character_id in self._character_ids()
            if (view := motivation_manager.get_for_character(character_id, viewer_id="director")) is not None
        ) if motivation_manager is not None and hasattr(motivation_manager, "get_for_character") else ()
        narrative_constraints = self.evaluator.to_narrative_constraints(constraint)
        candidates = self.planner.plan_from_state(
            goals, motivations, resources,
            world_state=public_world_state, presence=presences, locations=locations, current_time=current_time,
            pressure=getattr(self.session, "narrative_pressure", None),
            constraints=(*getattr(self.session, "narrative_constraints", ()), *narrative_constraints),
        )
        existing_keys = {(item.event_type, item.participants, item.conditions) for item in state.candidates}
        active_constraints = tuple(item for item in (*self.constraints, constraint)
                                   if item.status not in {DirectorConstraintStatus.BLOCKED, DirectorConstraintStatus.FAILED})
        adjusted_candidates = []
        for candidate in candidates:
            allowed, delta, _ = self.evaluator.evaluate_candidate(candidate, active_constraints)
            if allowed:
                adjusted_candidates.append(replace(candidate, pressure=max(0.0, min(1.0, candidate.pressure + delta))))
        candidates = tuple(adjusted_candidates)
        added = tuple(item for item in candidates if (item.event_type, item.participants, item.conditions) not in existing_keys)
        self.session.narrative_constraints = tuple((*getattr(self.session, "narrative_constraints", ()), *narrative_constraints))
        self.session.candidate_events = tuple((*state.candidates, *added))
        self.session.narrative_state = NarrativeState(
            state.threads, self.session.candidate_events, state.pressure
        )
        paths = self.path_finder.find_paths(
            intent, world_state=public_world_state, presences=presences, threads=state.threads,
            goals=goals,
            relationships=getattr(getattr(executor, "relationship_manager", None), "relationships", ()),
            emotions=getattr(self.session, "emotion_engine", None), candidate_events=self.session.candidate_events,
            constraints=active_constraints,
        )
        constraint = replace(constraint, status=DirectorConstraintStatus.SEARCHING if paths else DirectorConstraintStatus.BLOCKED)
        result = DirectorResult(intent, constraint, bool(paths), reason or "已登记为软叙事目标，等待因果条件与世界规则评估。",
                                paths, tuple(dict.fromkeys(thread for path in paths for thread in path.thread_ids)))
        self.constraints.append(constraint)
        self.history.append(result)
        self._sync_session()
        return result

    def _sync_session(self):
        self.session.director_constraints = tuple(self.constraints)
        self.session.director_history = tuple(self.history)

    def _character_ids(self):
        return tuple(item.character_id for item in getattr(self.session, "agent_contexts", ()))

    def remove_constraint(self, constraint_id):
        before = len(self.constraints)
        self.constraints = [item for item in self.constraints if item.id != constraint_id]
        self._sync_session()
        return len(self.constraints) != before

    def edit_constraint(self, constraint_id, text):
        old = next((item for item in self.constraints if item.id == constraint_id), None)
        if old is None:
            return False
        known = tuple((item.character_id, item.character_state.name)
                      for item in getattr(self.session, "agent_contexts", ()))
        intent = self.parser.parse(text, known)
        updated = replace(old, intent=intent, target=intent.target, priority=intent.priority,
                          constraint_type=intent.constraint_type, target_kind=intent.constraint_target,
                          category=intent.category, strength=intent.strength, status=DirectorConstraintStatus.PENDING)
        self.constraints = [updated if item.id == constraint_id else item for item in self.constraints]
        self._sync_session()
        return True

    @staticmethod
    def _public_world_state(world_state):
        if not hasattr(world_state, "get"):
            return {}
        allowed = {
            "location", "time", "stage", "world_phase", "danger_level",
            "resource_level", "energy_level", "environment_description",
        }
        return {
            key: world_state[key]
            for key in allowed
            if key in world_state and isinstance(world_state[key], (str, int, float, bool, type(None)))
        }
