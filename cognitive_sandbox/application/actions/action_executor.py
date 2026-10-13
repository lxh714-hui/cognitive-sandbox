from __future__ import annotations


class ActionExecutor:
    """Shared action boundary for player handlers and deterministic NPC actions."""

    def __init__(self, npc_event_executor=None):
        self.npc_event_executor = npc_event_executor
        self.authority_manager = None

    def execute(self, action, *, handler=None, context=None, timestamp=None, world_revision=0, actor_name=None):
        from cognitive_sandbox.application.npc.npc_action import NpcAction
        if isinstance(action, NpcAction):
            if self.npc_event_executor is None:
                raise RuntimeError("NPC event executor is not configured.")
            if self.authority_manager is not None:
                self.authority_manager.require_autonomous_permission(action.actor_id)
            return self.npc_event_executor.execute(
                action, timestamp=timestamp, world_revision=world_revision, actor_name=actor_name
            )
        if handler is None or context is None:
            raise TypeError("player actions require a handler and execution context.")
        authority_manager = getattr(context, "authority_manager", None)
        if authority_manager is not None:
            authority_manager.require_control_permission(
                action.actor_id,
                requester_id=getattr(getattr(context, "turn", None), "player_id", None),
            )
        return handler.handle(action, context)
