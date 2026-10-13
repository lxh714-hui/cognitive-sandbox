from __future__ import annotations

from dataclasses import replace

from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.relationship.relationship_rule import RelationshipRule
from cognitive_sandbox.relationship.relationship_state import RelationshipState


class RelationshipManager:
    """Maintain directional relationships and update them from deterministic rules."""

    DEFAULT_RULES = (
        RelationshipRule(("help_attempt", "player_helped_doctor", "player_helped"), trust_delta=20, respect_delta=10, direction="both"),
        RelationshipRule(("player_lied", "lied"), trust_delta=-20),
        RelationshipRule(("player_threatened", "weapon_threat"), fear_delta=20, hostility_delta=10, direction="target_to_actor"),
        RelationshipRule(("weapon_drawn", "weapon_draw"), fear_delta=8, hostility_delta=4, direction="target_to_actor"),
        RelationshipRule(("protect_attempt",), respect_delta=10, trust_delta=5, direction="target_to_actor"),
    )

    def __init__(self, relationships=(), rules=None, *, emotion_engine=None):
        self.rules = tuple(self.DEFAULT_RULES if rules is None else rules)
        if any(not isinstance(rule, RelationshipRule) for rule in self.rules):
            raise TypeError("rules must contain RelationshipRule values.")
        self._processed_event_ids: set[str] = set()
        self.emotion_engine = emotion_engine
        self.restore_relationships(relationships)

    @property
    def relationships(self) -> tuple[RelationshipState, ...]:
        return tuple(self._states[key] for key in sorted(self._states))

    def get_relationship(self, source_id: str, target_id: str) -> RelationshipState:
        return self._states.get((source_id, target_id), RelationshipState(source_id, target_id))

    def set_relationship(self, state: RelationshipState) -> None:
        if not isinstance(state, RelationshipState):
            raise TypeError("state must be a RelationshipState.")
        self._states[(state.source_id, state.target_id)] = state

    def for_character(self, character_id: str) -> tuple[RelationshipState, ...]:
        """Return only directed relationship entries owned by this character."""
        return tuple(state for state in self.relationships if state.source_id == character_id)

    def apply_event(self, event: WorldEvent) -> tuple[RelationshipState, ...]:
        if not isinstance(event, WorldEvent):
            raise TypeError("event must be a WorldEvent.")
        if event.event_id in self._processed_event_ids:
            return self.relationships
        self._processed_event_ids.add(event.event_id)
        event_type = event.event_type
        rules = tuple(rule for rule in self.rules if event_type in rule.event_types)
        if not rules:
            return self.relationships
        target = event.target_id
        if target is None:
            payload_target = event.payload.get("target_id")
            target = payload_target if isinstance(payload_target, str) and payload_target.strip() else None
        actor = event.actor_id
        if target is None or actor == target:
            return self.relationships
        for rule in rules:
            directions = ((actor, target),) if rule.direction == "actor_to_target" else (
                ((target, actor),) if rule.direction == "target_to_actor" else ((actor, target), (target, actor))
            )
            for source_id, target_id in directions:
                current = self.get_relationship(source_id, target_id)
                updated = replace(
                    current,
                    trust=_clamp(current.trust + rule.trust_delta),
                    respect=_clamp(current.respect + rule.respect_delta),
                    fear=_clamp(current.fear + rule.fear_delta),
                    affinity=_clamp(current.affinity + rule.affinity_delta),
                    hostility=_clamp(current.hostility + rule.hostility_delta),
                )
                self.set_relationship(updated)
                if self.emotion_engine is not None:
                    self.emotion_engine.relationship_changed(source_id, target_id, current, updated, event)
        return self.relationships

    def mark_events_processed(self, event_ids) -> None:
        values = tuple(event_ids)
        if any(not isinstance(item, str) or not item.strip() for item in values):
            raise ValueError("processed event IDs must be non-empty strings.")
        self._processed_event_ids.update(values)

    def restore_relationships(self, relationships) -> None:
        values = tuple(relationships)
        if any(not isinstance(item, RelationshipState) for item in values):
            raise TypeError("relationships must contain RelationshipState values.")
        keys = [(item.source_id, item.target_id) for item in values]
        if len(set(keys)) != len(keys):
            raise ValueError("relationships contain duplicate directional pairs.")
        self._states = dict(zip(keys, values))


def _clamp(value):
    return max(-100.0, min(100.0, float(value)))
