from __future__ import annotations

from cognitive_sandbox.domain.relationship import RelationshipState


class RelationshipInitializer:
    """Copy scenario-provided starting relationships without inferring role lore."""

    def initialize(
        self,
        role_description: str,
        *,
        source_id: str = "character",
        relationships=(),
    ) -> tuple[RelationshipState, ...]:
        if not isinstance(role_description, str) or not role_description.strip():
            raise ValueError("role_description must not be empty.")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("source_id must not be empty.")

        result = []
        for item in relationships:
            if isinstance(item, RelationshipState):
                result.append(item)
            elif isinstance(item, dict):
                result.append(RelationshipState(
                    source_id, item["target_id"], item["relation_type"], item.get("trust", 0.5),
                ))
            else:
                raise TypeError("relationships must contain RelationshipState or mapping values.")
        return tuple(result)
