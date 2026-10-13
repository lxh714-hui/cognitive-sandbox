from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from uuid import uuid4

from .emotional_memory import EmotionalMemory
from .emotional_state import EMOTION_FIELDS, EmotionalState
from .emotion_decay import EmotionDecay
from .emotion_event import EmotionEvent
from .emotion_rule import EmotionRule


@dataclass(frozen=True)
class EmotionUpdateResult:
    character_id: str
    state: EmotionalState
    events: tuple[EmotionEvent, ...]
    memories: tuple[EmotionalMemory, ...] = ()


class EmotionEngine:
    """Apply deterministic, source-traceable emotion rules and time decay."""

    DEFAULT_RULES = (
        EmotionRule(("friend_injured", "character_injured"), (("attachment", .2), ("fear", .15), ("guilt", .05)),
                    "failed_to_protect", .7, (("fear", .05), ("surprise", .1)), "protective"),
        EmotionRule(("anomaly_detected", "anomaly_found"), (("fear", .15), ("surprise", .2), ("curiosity", .1)),
                    "witnessed_anomaly", learned_tendency="investigative"),
        EmotionRule(("player_lied", "betrayal", "lied"), (("anger", .12), ("sadness", .08), ("trust", -.1)),
                    "experienced_betrayal", learned_tendency="cautious"),
        EmotionRule(("help_attempt", "player_helped"), (("attachment", .08), ("joy", .1), ("hope", .05)),
                    "received_help", learned_tendency="protective"),
    )

    def __init__(self, states=(), history=(), memories=(), *, rules=None, decay=None, memory_threshold=.2):
        self.rules = tuple(self.DEFAULT_RULES if rules is None else rules)
        if any(not isinstance(rule, EmotionRule) for rule in self.rules):
            raise TypeError("rules must contain EmotionRule values.")
        self.decay_model = decay or EmotionDecay()
        self.memory_threshold = float(memory_threshold)
        if not 0 <= self.memory_threshold <= 1:
            raise ValueError("memory_threshold must be between 0 and 1.")
        self._states = {}
        for character_id, state in dict(states).items() if hasattr(states, "items") else tuple(states):
            self.set_state(character_id, state)
        self._history = list(history)
        self._memories = {}
        for character_id, memory in memories:
            self.add_memory(character_id, memory)
        if any(not isinstance(event, EmotionEvent) for event in self._history):
            raise TypeError("history must contain EmotionEvent values.")
        self._applied_changes = {
            (event.character_id, event.source_event_id, event.emotion_type, event.reason)
            for event in self._history
        }

    @property
    def states(self):
        return dict(self._states)

    @property
    def history(self):
        return tuple(self._history)

    @property
    def memories(self):
        return tuple((character_id, memory) for character_id in sorted(self._memories)
                     for memory in self._memories[character_id])

    def state_for(self, character_id: str) -> EmotionalState:
        return self._states.get(character_id, EmotionalState())

    def history_for(self, character_id: str) -> tuple[EmotionEvent, ...]:
        return tuple(event for event in self._history if event.character_id == character_id)

    def memories_for(self, character_id: str) -> tuple[EmotionalMemory, ...]:
        return tuple(self._memories.get(character_id, ()))

    def set_state(self, character_id: str, state: EmotionalState) -> None:
        if not isinstance(character_id, str) or not character_id.strip():
            raise ValueError("character_id must not be empty.")
        if not isinstance(state, EmotionalState):
            raise TypeError("state must be EmotionalState.")
        self._states[character_id] = state

    def add_memory(self, character_id: str, memory: EmotionalMemory) -> None:
        if not isinstance(character_id, str) or not character_id.strip():
            raise ValueError("character_id must not be empty.")
        if not isinstance(memory, EmotionalMemory):
            raise TypeError("memory must be EmotionalMemory.")
        values = self._memories.setdefault(character_id, [])
        if any(item.event_id == memory.event_id for item in values):
            return
        values.append(memory)

    def apply_event(self, world_event, character_id: str, relationships=(), *, timestamp=None) -> EmotionUpdateResult:
        if not isinstance(character_id, str) or not character_id.strip():
            raise ValueError("character_id must not be empty.")
        event_type = str(getattr(world_event, "event_type", ""))
        matching = [rule for rule in self.rules if event_type in rule.event_types]
        if not matching:
            return EmotionUpdateResult(character_id, self.state_for(character_id), ())
        relation = _relevant_relationship(character_id, world_event, relationships)
        trust = _normalized_trust(getattr(relation, "trust", 0.0)) if relation is not None else 0.0
        timestamp = timestamp or getattr(world_event, "timestamp", None) or datetime.now(timezone.utc).isoformat()
        state = self.state_for(character_id)
        events = []
        memory_tendencies = []
        for rule in matching:
            if all((character_id, world_event.event_id, emotion, rule.reason) in self._applied_changes
                   for emotion, _ in rule.deltas):
                continue
            deltas = rule.deltas
            if rule.relationship_trust_min is not None and trust < rule.relationship_trust_min:
                deltas = rule.unrelated_deltas
            for emotion, delta in deltas:
                if emotion not in EMOTION_FIELDS:
                    continue
                old = getattr(state, emotion)
                new = max(0.0, min(1.0, old + delta))
                applied = new - old
                state = replace(state, **{emotion: new})
                if applied:
                    traced = EmotionEvent(character_id, world_event.event_id, emotion, applied, rule.reason, timestamp)
                    events.append(traced)
                    self._applied_changes.add((character_id, world_event.event_id, emotion, rule.reason))
            if rule.learned_tendency and deltas:
                memory_tendencies.append((rule.learned_tendency, rule.reason))
        self._states[character_id] = state
        self._history.extend(events)
        new_memories = []
        impact = {event.emotion_type: event.delta for event in events}
        if impact and sum(abs(value) for value in impact.values()) >= self.memory_threshold:
            tendency, reason = memory_tendencies[0] if memory_tendencies else ("cautious", "significant_emotional_event")
            memory = EmotionalMemory(world_event.event_id, impact, tendency,
                                     min(1.0, max(abs(value) for value in impact.values()) + .2))
            self.add_memory(character_id, memory)
            new_memories.append(memory)
        return EmotionUpdateResult(character_id, state, tuple(events), tuple(new_memories))

    def handle_event(self, world_event, context=None):
        """EventPipeline listener: apply rules to participants and decay on world ticks."""
        if getattr(world_event, "event_type", "") == "world_tick":
            minutes = getattr(world_event, "payload", {}).get("elapsed_minutes", 0)
            if isinstance(minutes, (int, float)) and not isinstance(minutes, bool) and minutes >= 0:
                character_ids = set(self._states)
                character_ids.update(
                    item.character_id for item in getattr(context, "agent_contexts", ())
                    if isinstance(getattr(item, "character_id", None), str)
                )
                return tuple(
                    self.decay(character_id, float(minutes) / 1440.0,
                               source_event_id=world_event.event_id,
                               timestamp=world_event.timestamp)
                    for character_id in sorted(character_ids)
                )
            return ()
        participants = tuple(dict.fromkeys(
            value for value in (getattr(world_event, "actor_id", None), getattr(world_event, "target_id", None))
            if isinstance(value, str) and value.strip()
        ))
        manager = getattr(context, "relationship_manager", None)
        results = []
        for character_id in participants:
            relationships = manager.for_character(character_id) if manager is not None else ()
            result = self.apply_event(world_event, character_id, relationships)
            if result.events:
                results.append(result)
        return tuple(results)

    def relationship_changed(self, source_id, target_id, old, new, world_event):
        trust_delta = float(getattr(new, "trust", 0)) - float(getattr(old, "trust", 0))
        affinity_delta = float(getattr(new, "affinity", 0)) - float(getattr(old, "affinity", 0))
        if trust_delta == 0 and affinity_delta == 0:
            return EmotionUpdateResult(source_id, self.state_for(source_id), ())
        relation_scale = 100 if abs(trust_delta) > 1 or abs(affinity_delta) > 1 else 1
        magnitude = min(.2, abs(trust_delta + affinity_delta) / relation_scale * .2)
        if trust_delta < 0:
            rule = EmotionRule((world_event.event_type,), (("anger", magnitude), ("sadness", magnitude * .6)),
                               "relationship_trust_decreased", learned_tendency="cautious")
        else:
            rule = EmotionRule((world_event.event_type,), (("attachment", magnitude), ("joy", magnitude * .5)),
                               "relationship_trust_increased", learned_tendency="protective")
        # Reuse the same bounded update and trace mechanism without changing the world event.
        temporary = EmotionEngine(( (source_id, self.state_for(source_id)), ), rules=(rule,),
                                  memory_threshold=self.memory_threshold)
        result = temporary.apply_event(world_event, source_id, timestamp=getattr(world_event, "timestamp", None))
        self._states[source_id] = result.state
        self._history.extend(result.events)
        for memory in result.memories:
            self.add_memory(source_id, memory)
        return result

    def decay(self, character_id: str, elapsed_days: float, *, source_event_id=None, timestamp=None) -> EmotionUpdateResult:
        old = self.state_for(character_id)
        new = self.decay_model.apply(old, elapsed_days)
        source_event_id = source_event_id or f"time_decay:{character_id}:{elapsed_days}"
        timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        events = tuple(
            EmotionEvent(character_id, source_event_id, field, getattr(new, field) - getattr(old, field),
                         "time_decay", timestamp)
            for field in EMOTION_FIELDS if getattr(new, field) != getattr(old, field)
        )
        self._states[character_id] = new
        self._history.extend(events)
        return EmotionUpdateResult(character_id, new, events)


def _normalized_trust(value):
    value = float(value or 0)
    return max(0.0, min(1.0, value / 100 if abs(value) > 1 else value))


def _relevant_relationship(character_id, event, relationships):
    involved = {getattr(event, "actor_id", None), getattr(event, "target_id", None)}
    involved.update(item for item in getattr(event, "payload", {}).values() if isinstance(item, str))
    return next((relation for relation in relationships
                 if getattr(relation, "source_id", None) == character_id
                 and getattr(relation, "target_id", None) in involved), None)
