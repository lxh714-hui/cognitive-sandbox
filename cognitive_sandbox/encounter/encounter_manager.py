from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from uuid import uuid4
from collections.abc import Mapping

from cognitive_sandbox.domain.world_events import WorldEvent
from .encounter_candidate import EncounterCandidate, EncounterStatus, EncounterTrajectory
from .encounter_evaluator import EncounterEvaluator
from .encounter_generator import EncounterGenerator
from .encounter_memory import EncounterHistoryRecord, EncounterMemory


@dataclass(frozen=True)
class EncounterSnapshot:
    candidates: tuple[EncounterCandidate, ...] = ()
    history: tuple[EncounterHistoryRecord, ...] = ()
    memories: tuple[EncounterMemory, ...] = ()
    trajectories: tuple[EncounterTrajectory, ...] = ()
    processed_event_ids: tuple[str, ...] = ()

    def __post_init__(self):
        for field, kind in (("candidates", EncounterCandidate), ("history", EncounterHistoryRecord),
                            ("memories", EncounterMemory), ("trajectories", EncounterTrajectory)):
            values = tuple(getattr(self, field))
            if any(not isinstance(item, kind) for item in values):
                raise TypeError(f"{field} must contain {kind.__name__} values.")
            object.__setattr__(self, field, values)
        object.__setattr__(self, "processed_event_ids", tuple(self.processed_event_ids))
        if any(not isinstance(item, str) or not item.strip() for item in self.processed_event_ids):
            raise ValueError("processed_event_ids must contain non-empty strings.")


class EncounterManager:
    """Creates optional social encounters from co-located character actions."""

    ACTION_EVENTS = frozenset({
        "help_attempt", "protect_attempt", "observe_action", "dialogue_event", "talk_attempt",
        "player_traveled", "travel_completed",
        "npc_patrolled", "npc_materials_collected", "doctor_repaired_clinic", "npc_socialized",
        "npc_investigated", "npc_observed", "npc_worked", "npc_rested", "npc_traveled", "npc_organized",
    })

    def __init__(self, *, authority_manager=None, relationship_manager=None, relationship_lifecycle_manager=None,
                 emotion_engine=None, cognitive_engine=None, knowledge_retriever=None,
                 character_minds=None, goal_manager=None, presence_manager=None, location_manager=None,
                 snapshot: EncounterSnapshot | None = None, generator=None, evaluator=None,
                 window_hours=8, clock=None):
        self.authority_manager = authority_manager
        self.relationship_manager = relationship_manager
        self.relationship_lifecycle_manager = relationship_lifecycle_manager
        self.emotion_engine = emotion_engine
        self.cognitive_engine = cognitive_engine
        self.knowledge_retriever = knowledge_retriever
        self.character_minds = dict(character_minds or {})
        self.goal_manager = goal_manager
        self.presence_manager = presence_manager
        self.location_manager = location_manager
        self.generator = generator or EncounterGenerator()
        self.evaluator = evaluator or EncounterEvaluator()
        self.window_hours = float(window_hours)
        if self.window_hours <= 0:
            raise ValueError("window_hours must be positive.")
        self._clock = clock or (lambda: datetime.now(timezone.utc).isoformat())
        snapshot = snapshot or EncounterSnapshot()
        if not isinstance(snapshot, EncounterSnapshot):
            raise TypeError("snapshot must be EncounterSnapshot.")
        self._candidates = {item.candidate_id: item for item in snapshot.candidates}
        self._history = list(snapshot.history)
        self._memories = list(snapshot.memories)
        self._trajectories = list(snapshot.trajectories)
        self._processed = set(snapshot.processed_event_ids)

    @property
    def candidates(self):
        return tuple(self._candidates[key] for key in sorted(self._candidates))

    @property
    def history(self):
        return tuple(self._history)

    @property
    def memories(self):
        return tuple(self._memories)

    def snapshot(self):
        return EncounterSnapshot(self.candidates, self.history, self.memories,
                                 tuple(self._trajectories), tuple(sorted(self._processed)))

    def handle_event(self, event, context=None):
        if event.event_id in self._processed:
            return ()
        self._processed.add(event.event_id)
        if event.event_type == "world_tick":
            self._expire(event.timestamp)
            return ()
        if event.event_type == "social_encounter":
            self._interpret_encounter(event)
            return ()
        if event.event_type not in self.ACTION_EVENTS and not str(event.event_type).startswith("npc_"):
            return ()
        actor_id = event.actor_id
        if not isinstance(actor_id, str) or not actor_id.strip() or actor_id == "system":
            return ()
        if not self._authorized_actor(actor_id):
            return ()
        location = self._event_location(event, actor_id)
        if not location:
            return ()
        if event.event_type in {"npc_traveled", "player_traveled", "travel_completed"}:
            self._apply_completed_travel(actor_id, location)
        timestamp = event.timestamp or self._clock()
        if not self._presence_allows(actor_id, location):
            return ()
        trajectory = EncounterTrajectory(
            actor_id, str(event.payload.get("action_type", event.event_type)), location,
            timestamp, event.event_id, self._public_activity(event),
        )
        self._trajectories.append(trajectory)
        self._trajectories = self._trajectories[-256:]
        results = []
        for other in tuple(self._trajectories[:-1]):
            if other.character_id == actor_id or not self._same_location(other.location, location):
                continue
            if not self._within_window(other.timestamp, timestamp):
                continue
            if not self._authorized_actor(other.character_id) or not self._presence_allows(other.character_id, other.location):
                continue
            try:
                normalized_other = replace(other, location=self._canonical_location(other.location))
                normalized_current = replace(trajectory, location=self._canonical_location(location))
                candidate = self.generator.generate(normalized_other, normalized_current, location=location)
            except (TypeError, ValueError):
                continue
            if candidate.candidate_id in self._candidates:
                continue
            candidate = self.evaluator.evaluate(
                candidate,
                goals_a=self._goals(candidate.character_a), goals_b=self._goals(candidate.character_b),
                relationship_a=self._relationship(candidate.character_a, candidate.character_b),
                relationship_b=self._relationship(candidate.character_b, candidate.character_a),
                stage_a=self._stage(candidate.character_a, candidate.character_b),
                stage_b=self._stage(candidate.character_b, candidate.character_a),
                emotion_a=self._emotion(candidate.character_a), emotion_b=self._emotion(candidate.character_b),
                cognition_a=self._cognition(candidate.character_a), cognition_b=self._cognition(candidate.character_b),
                social_density=self._social_density(location),
                narrative_pressure=self._pressure(context),
            )
            self._candidates[candidate.candidate_id] = candidate
            if candidate.status is EncounterStatus.AVAILABLE:
                triggered = replace(candidate, status=EncounterStatus.TRIGGERED)
                self._candidates[candidate.candidate_id] = triggered
                results.append(self._make_event(triggered, timestamp, event))
        return tuple(results)

    def recent_for(self, character_id: str, *, limit=10):
        records = [item for item in self._history
                   if item.character_a == character_id or item.character_b == character_id]
        return tuple(records[-max(0, int(limit)):]) if limit else ()

    def public_recent_for(self, character_id: str, *, limit=5):
        records = self.recent_for(character_id, limit=limit)
        counts = {}
        for item in self._history:
            if item.character_a == character_id:
                other = item.character_b
            elif item.character_b == character_id:
                other = item.character_a
            else:
                continue
            counts[other] = counts.get(other, 0) + 1
        result = []
        for item in records:
            other_id = item.character_b if item.character_a == character_id else item.character_a
            mind = self.character_minds.get(other_id)
            identity = getattr(mind, "identity", None)
            name = getattr(identity, "name", None)
            if not isinstance(name, str) or not name.strip():
                continue
            result.append({
                "name": name, "location": item.location, "familiarity": min(1.0, counts[other_id] * .12),
                "shared_experience_count": counts[other_id], "timestamp": item.timestamp,
            })
        return tuple(result)

    def _make_event(self, candidate, timestamp, source_event):
        encounter_id = f"encounter_{uuid4().hex}"
        description = "兩人因行動軌跡重合，在同一地點有了第一次接觸。"
        event = WorldEvent(
            encounter_id, source_event.branch_id, source_event.world_id, "social_encounter", candidate.character_a,
            {"description": description, "candidate_id": candidate.candidate_id,
             "encounter_id": encounter_id, "importance": .35,
             "public_activity_a": candidate.activity_a, "public_activity_b": candidate.activity_b},
            source_event.world_revision, target_id=candidate.character_b,
            location=candidate.location, timestamp=timestamp,
        )
        self._history.append(EncounterHistoryRecord(
            encounter_id, candidate.candidate_id, candidate.character_a, candidate.character_b,
            candidate.location, timestamp, candidate.source_event_ids, description,
        ))
        self._memories.extend((
            EncounterMemory(candidate.character_a, candidate.character_b, encounter_id, encounter_id,
                            "first_contact", timestamp, description),
            EncounterMemory(candidate.character_b, candidate.character_a, encounter_id, encounter_id,
                            "first_contact", timestamp, description),
        ))
        return event

    def _interpret_encounter(self, event):
        if self.cognitive_engine is None:
            return
        a, b = event.actor_id, event.target_id
        if not a or not b:
            return
        activity_a = str(event.payload.get("public_activity_a", ""))
        activity_b = str(event.payload.get("public_activity_b", ""))
        public = str(event.payload.get("description", "兩人在同一地點有了接觸。"))
        private_a = self._visible_knowledge(a)
        private_b = self._visible_knowledge(b)
        # Each person receives only the other person's publicly observable action.
        self.cognitive_engine.interpret_event(a, event, (*private_a, public, _visible_activity(activity_b)))
        self.cognitive_engine.interpret_event(b, event, (*private_b, public, _visible_activity(activity_a)))

    def _visible_knowledge(self, character_id):
        if self.knowledge_retriever is None:
            return ()
        try:
            from cognitive_sandbox.knowledge.retrieval.knowledge_query import KnowledgeQuery
            records = self.knowledge_retriever.retrieve(character_id, KnowledgeQuery(limit=100))
        except (TypeError, ValueError, AttributeError):
            return ()
        return tuple(record.known_content for record in records
                     if getattr(record, "owner_id", None) == character_id
                     and isinstance(getattr(record, "known_content", None), str)
                     and record.known_content.strip())

    def _authorized_actor(self, character_id):
        if self.authority_manager is None:
            return True
        authority = self.authority_manager.authority_for(character_id)
        if authority is None:
            return False
        if authority.controllable:
            return character_id == self.authority_manager.player_character_id
        return self.authority_manager.check_autonomous_permission(character_id)

    def _event_location(self, event, actor_id):
        if isinstance(event.location, str) and event.location.strip():
            return event.location
        parameters = event.payload.get("parameters", {})
        if isinstance(parameters, Mapping):
            place = parameters.get("location")
            if isinstance(place, str) and place.strip():
                return place
        presence = self.presence_manager.get(actor_id) if self.presence_manager else None
        return getattr(presence, "current_location", None)

    def _presence_allows(self, character_id, location):
        if self.presence_manager is None:
            return True
        presence = self.presence_manager.get(character_id)
        if presence is None:
            return False
        state = getattr(presence, "availability", None)
        if getattr(state, "value", state) not in {"ACTIVE", "INTRODUCED"}:
            return False
        current = getattr(presence, "current_location", None)
        return not current or self._same_location(current, location)

    def _apply_completed_travel(self, character_id, location):
        if self.presence_manager is None:
            return
        presence = self.presence_manager.get(character_id)
        if presence is None or getattr(presence, "current_location", None) == location:
            return
        try:
            self.presence_manager.move_to(character_id, location, travel_completed=True)
        except (KeyError, ValueError):
            # A travel event cannot introduce a character or bypass entry rules.
            return

    def _same_location(self, first, second):
        return _normalize(self._canonical_location(first)) == _normalize(self._canonical_location(second))

    def _canonical_location(self, value):
        if self.location_manager is None:
            return value
        for item in getattr(self.location_manager, "locations", ()):
            if value in (getattr(item, "location_id", None), getattr(item, "name", None)):
                return getattr(item, "location_id", value)
        return value

    def _within_window(self, first, second):
        try:
            a, b = _datetime(first), _datetime(second)
            return abs((a - b).total_seconds()) <= self.window_hours * 3600
        except (TypeError, ValueError):
            return first == second

    def _expire(self, timestamp):
        now = _safe_datetime(timestamp)
        if now is None:
            return
        for key, candidate in tuple(self._candidates.items()):
            if candidate.status not in {EncounterStatus.POSSIBLE, EncounterStatus.AVAILABLE}:
                continue
            try:
                created = _safe_datetime(candidate.time_window.split("/")[-1])
            except (TypeError, ValueError):
                created = None
            if created and (now - created).total_seconds() > self.window_hours * 3600:
                self._candidates[key] = replace(candidate, status=EncounterStatus.EXPIRED)

    def _goals(self, character_id):
        return tuple(goal for goal in getattr(self.goal_manager, "goals", ())
                     if getattr(goal, "owner_id", None) == character_id
                     and str(getattr(getattr(goal, "status", None), "value", getattr(goal, "status", "ACTIVE"))).upper()
                     not in {"FAILED", "SATISFIED", "COMPLETED"}) if self.goal_manager else ()

    def _relationship(self, source, target):
        return self.relationship_manager.get_relationship(source, target) if self.relationship_manager else None

    def _stage(self, source, target):
        return self.relationship_lifecycle_manager.stage_for(source, target) if self.relationship_lifecycle_manager else "UNKNOWN"

    def _emotion(self, character_id):
        return self.emotion_engine.state_for(character_id) if self.emotion_engine else None

    def _cognition(self, character_id):
        return self.cognitive_engine.context_for(character_id) if self.cognitive_engine else None

    def _social_density(self, location):
        if self.location_manager is None:
            return .25
        state = next((item for item in self.location_manager.locations
                      if self._same_location(item.location_id, location)), None)
        tags = tuple(str(tag).casefold() for tag in getattr(state, "tags", ())) if state else ()
        if any("social_density_high" in tag or "social" in tag or "market" in tag for tag in tags):
            return .8
        return .25

    @staticmethod
    def _pressure(context):
        pressure = getattr(context, "narrative_pressure", None)
        return float(getattr(pressure, "urgency", 0) or 0) if pressure else 0.0

    @staticmethod
    def _public_activity(event):
        payload = event.payload
        text = payload.get("description", "")
        if isinstance(text, str) and text.strip():
            # Description is a public event observation, not a goal or private state.
            return text
        action = str(payload.get("action_type", event.event_type))
        return _visible_activity(action)


def _normalize(value):
    return " ".join(str(value).strip().casefold().split())


def _safe_datetime(value):
    try:
        return _datetime(value)
    except (TypeError, ValueError):
        return None


def _datetime(value):
    if not isinstance(value, str):
        raise TypeError("timestamp must be a string.")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _visible_activity(value):
    text = str(value).casefold()
    if any(token in text for token in ("investigat", "调查", "线索")):
        return "对方正在调查附近可见的线索。"
    if any(token in text for token in ("observ", "查看", "观察")):
        return "对方正在观察周围环境。"
    if any(token in text for token in ("social", "talk", "交谈")):
        return "对方正在与附近的人交谈。"
    return "对方在此处进行日常活动。"


__all__ = ["EncounterManager", "EncounterSnapshot"]
