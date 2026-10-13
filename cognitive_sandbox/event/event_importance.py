from __future__ import annotations


_LEVELS = {
    "world_tick": 0,
    "npc_worked": 0,
    "npc_rested": 0,
    "npc_organized": 0,
    "npc_observed": 1,
    "observe_action": 1,
    "npc_socialized": 1,
    "dialogue_event": 1,
    "npc_investigated": 2,
    "social_encounter": 2,
    "neighborhood_rumor": 2,
    "director_custom_event": 2,
}


def event_importance_level(event) -> int:
    """Return a stable 0–3 presentation/report category for a world event record."""
    metadata = getattr(event, "metadata", {}) or {}
    explicit = metadata.get("importance_level") if hasattr(metadata, "get") else None
    if isinstance(explicit, int) and not isinstance(explicit, bool) and 0 <= explicit <= 3:
        return explicit
    event_type = getattr(event, "event_type", "")
    if event_type in _LEVELS:
        return _LEVELS[event_type]
    value = getattr(event, "importance", 0.0)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return 3 if value >= .85 else 2 if value >= .65 else 1 if value >= .35 else 0
    return 1
