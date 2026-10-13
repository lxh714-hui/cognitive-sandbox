from __future__ import annotations

from uuid import uuid4

from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.application.npc.npc_action import NpcAction


class NpcActionExecutor:
    """Translate an approved generic NPC action into a scenario-defined event."""

    DEFAULT_EVENT_TYPES = {
        "patrol": "npc_patrolled", "collect": "npc_resource_collected",
        "repair": "npc_repaired", "move": "npc_moved", "interact": "npc_interacted",
        "socialize": "npc_socialized", "investigate": "npc_investigated",
        "observe": "npc_observed", "work": "npc_worked", "rest": "npc_rested",
        "travel": "npc_traveled", "organize": "npc_organized",
    }
    EVENT_TYPES = DEFAULT_EVENT_TYPES

    def __init__(self, *, world_id="world", branch_id="main", id_factory=None,
                 event_types=None, action_policies=None, descriptions=None):
        self.world_id = world_id
        self.branch_id = branch_id
        self._id_factory = id_factory or (lambda: uuid4().hex)
        self.event_types = {**self.DEFAULT_EVENT_TYPES, **dict(event_types or {})}
        self.action_policies = dict(action_policies or {})
        self.descriptions = dict(descriptions or {})

    def event_type_for(self, action_type):
        return self.event_types.get(action_type)

    def execute(self, action: NpcAction, *, timestamp: str | None = None,
                world_revision: int = 0, actor_name: str | None = None):
        if not isinstance(action, NpcAction):
            raise TypeError("action must be NpcAction.")
        event_type = self.event_type_for(action.action_type)
        if event_type is None:
            return None
        policy = self.action_policies.get(action.action_type, {})
        parameters = action.parameters
        lifecycle = parameters.get("event_lifecycle", policy.get("lifecycle", "REPEATABLE"))
        cooldown = parameters.get("cooldown_days", policy.get("cooldown_days", 0))
        importance = parameters.get("event_importance", policy.get("importance", 1))
        description = parameters.get("description") or self.descriptions.get(action.action_type) or action.reason
        return WorldEvent(
            f"event_{self._id_factory()}", self.branch_id, self.world_id, event_type,
            action.actor_id,
            {
                "action_type": action.action_type, "reason": action.reason,
                "parameters": dict(parameters), "importance": policy.get("importance_score", .4),
                "importance_level": importance, "event_lifecycle": lifecycle,
                "cooldown_days": cooldown,
                "lifecycle_key": parameters.get("lifecycle_key", event_type),
                "lifecycle_active": parameters.get("lifecycle_active", lifecycle == "ONGOING"),
                **({"actor_name": actor_name} if isinstance(actor_name, str) and actor_name.strip() else {}),
                "description": description,
            }, world_revision, target_id=action.target,
            location=(parameters.get("location") if isinstance(parameters.get("location"), str)
                      and parameters.get("location").strip() else None),
            timestamp=timestamp,
        )
