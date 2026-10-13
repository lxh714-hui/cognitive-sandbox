from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationMetrics:
    """Bounded, descriptive measures of activity in an offline run."""

    activity_rate: float
    character_independence: float
    knowledge_isolation: float
    emotion_dynamics: float
    narrative_growth: float
    knowledge_leaks: int = 0
    unique_actions: int = 0
    repeated_actions: int = 0
    conflict_related_events: int = 0
    relationship_changes: int = 0
    goal_transitions: int = 0
    important_events: int = 0
    active_conflicts: int = 0
    conflict_types: tuple[str, ...] = ()
    resolved_conflicts: int = 0
    transformed_conflicts: int = 0
    conflict_related_actions: int = 0

    def __post_init__(self):
        for name in (
            "activity_rate", "character_independence", "knowledge_isolation",
            "emotion_dynamics", "narrative_growth",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1.")
            object.__setattr__(self, name, float(value))
        if isinstance(self.knowledge_leaks, bool) or not isinstance(self.knowledge_leaks, int) or self.knowledge_leaks < 0:
            raise ValueError("knowledge_leaks must be a non-negative integer.")
        for name in ("unique_actions", "repeated_actions", "conflict_related_events",
                     "relationship_changes", "goal_transitions", "important_events", "active_conflicts",
                     "resolved_conflicts", "transformed_conflicts", "conflict_related_actions"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")
        object.__setattr__(self, "conflict_types", tuple(self.conflict_types))

    @classmethod
    def calculate(cls, *, tick_count, events, npc_count, emotion_changes,
                  knowledge_leaks, thread_changes, relationship_changes=(), goal_transitions=(),
                  conflicts=(), transformed_conflicts=0):
        if tick_count < 0 or npc_count < 0:
            raise ValueError("tick_count and npc_count must be non-negative.")
        activity_events = sum(event.event_type != "world_tick" for event in events)
        npc_actions = sum(event.event_type.startswith("npc_") for event in events)
        action_keys = []
        conflict_events = 0
        conflict_actions = 0
        from cognitive_sandbox.event.event_importance import event_importance_level
        important_events = 0
        for event in events:
            metadata = getattr(event, "metadata", {}) or {}
            action_type = metadata.get("action_type") if hasattr(metadata, "get") else None
            if action_type and event.event_type.startswith("npc_"):
                actor_ids = getattr(event, "actor_ids", ())
                action_keys.append((actor_ids[0] if actor_ids else "", action_type))
            searchable = " ".join((getattr(event, "event_type", ""), str(metadata))).casefold()
            conflict_events += int(any(token in searchable for token in ("conflict", "threat", "argue", "hostil")))
            parameters = metadata.get("parameters", {}) if hasattr(metadata, "get") else {}
            conflict_actions += int(bool(parameters.get("conflict_response"))
                                    if hasattr(parameters, "get") else False)
            important_events += int(event_importance_level(event) >= 2)
        unique_actions = len(set(action_keys))
        conflicts = tuple(conflicts)
        active = tuple(item for item in conflicts if getattr(getattr(item, "status", None), "value", getattr(item, "status", ""))
                        in {"emerging", "active", "escalating", "stable", "escalated"})
        resolved = sum(getattr(getattr(item, "status", None), "value", getattr(item, "status", ""))
                       in {"resolved", "accepted"} for item in conflicts)
        transformed = sum(getattr(getattr(item, "status", None), "value", getattr(item, "status", ""))
                         == "transformed" for item in conflicts)
        return cls(
            min(1.0, activity_events / max(1, tick_count)),
            min(1.0, npc_actions / max(1, npc_count * max(1, tick_count))),
            1.0 if knowledge_leaks == 0 else 0.0,
            min(1.0, emotion_changes / max(1, npc_count + 1)),
            1.0 if thread_changes else 0.0,
            knowledge_leaks,
            unique_actions,
            max(0, len(action_keys) - unique_actions),
            conflict_events,
            len(tuple(relationship_changes)),
            len(tuple(goal_transitions)),
            important_events,
            len(active), tuple(sorted({getattr(getattr(item, "conflict_type", None), "value",
                                                 getattr(item, "conflict_type", "")) for item in active})),
            resolved, max(int(transformed_conflicts), transformed), conflict_actions,
        )
