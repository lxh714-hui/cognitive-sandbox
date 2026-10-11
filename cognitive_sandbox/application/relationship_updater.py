from __future__ import annotations

from collections.abc import Iterable

from cognitive_sandbox.domain.relationship import RelationshipState
from cognitive_sandbox.domain.world_events import WorldEvent


class RelationshipUpdater:
    """Apply small event-based trust adjustments without mutating relationships."""

    _ADJUSTMENTS = {
        "help_attempt": {"care": 0.1},
        "protect_attempt": {"comrade": 0.05},
        "action_failed": {"*": -0.05},
    }

    def update(
        self,
        existing_relationships: Iterable[RelationshipState],
        event: WorldEvent,
    ) -> tuple[RelationshipState, ...]:
        if isinstance(existing_relationships, (str, bytes)):
            raise TypeError("existing_relationships must contain RelationshipState values.")
        relationships = tuple(existing_relationships)
        if any(not isinstance(item, RelationshipState) for item in relationships):
            raise TypeError("existing_relationships must contain only RelationshipState values.")
        if not isinstance(event, WorldEvent):
            raise TypeError("event must be a WorldEvent.")

        adjustments = self._ADJUSTMENTS.get(event.event_type)
        if adjustments is None:
            return relationships

        updated: list[RelationshipState] = []
        for relation in relationships:
            delta = adjustments.get(relation.relation_type, adjustments.get("*"))
            if delta is None:
                updated.append(relation)
                continue
            trust = min(1.0, max(0.0, relation.trust + delta))
            updated.append(
                RelationshipState(
                    source_id=relation.source_id,
                    target_id=relation.target_id,
                    relation_type=relation.relation_type,
                    trust=trust,
                )
            )
        return tuple(updated)
