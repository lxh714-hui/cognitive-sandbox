from __future__ import annotations

from cognitive_sandbox.domain.relationship import RelationshipState


class RelationshipInitializer:
    """Create a role's simple pre-existing relationship template."""

    def initialize(
        self,
        role_description: str,
        *,
        source_id: str = "character",
    ) -> tuple[RelationshipState, ...]:
        if not isinstance(role_description, str) or not role_description.strip():
            raise ValueError("role_description must not be empty.")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("source_id must not be empty.")

        description = role_description.casefold()
        if "医生" in description:
            return (RelationshipState(source_id, "patient", "care", 0.6),)
        if "士兵" in description:
            return (RelationshipState(source_id, "comrade", "comrade", 0.8),)
        return ()
