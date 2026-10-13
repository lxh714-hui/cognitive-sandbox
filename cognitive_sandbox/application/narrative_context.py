from __future__ import annotations

from types import MappingProxyType


class NarrativeContextBuilder:
    """Build a small, player-safe scene snapshot for dialogue and action replies."""

    def build(self, *, actor_id, world_state, clock=None, timeline=None, presence_manager=None):
        state = world_state if hasattr(world_state, "get") else {}
        presence = presence_manager.get(actor_id) if presence_manager is not None else None
        location = getattr(presence, "current_location", None) or state.get("location")
        when = clock.current_time() if clock is not None else None
        time_text = when.strftime("Day %d %H:%M") if when is not None else ""
        recent = []
        for event in tuple(getattr(timeline, "events", ()))[-8:]:
            metadata = getattr(event, "metadata", {}) or {}
            if metadata.get("visibility") in {"hidden", "private"}:
                continue
            participants = (*getattr(event, "actor_ids", ()), *getattr(event, "target_ids", ()))
            if actor_id not in participants:
                continue
            text = metadata.get("public_description") or metadata.get("description")
            if isinstance(text, str) and text.strip():
                recent.append(text.strip())
        activity = state.get("player_activity")
        state_text = {
            "awake": "你已经起身。", "eat": "你刚用过餐。", "work": "你刚处理过工作。",
            "rest": "你刚休息过。", "traveling": "你刚抵达这里。",
            "looking_for_someone": "你正在寻找一位熟悉的人。",
        }.get(activity, "")
        result = {
            "location": location if isinstance(location, str) else "",
            "time": time_text,
            "recent_events": tuple(recent[-3:]),
            "current_state": state_text,
            "visible_characters": tuple(state.get("visible_characters", ()))
                if isinstance(state.get("visible_characters", ()), (tuple, list)) else (),
            "visible_objects": tuple(state.get("visible_objects", ()))
                if isinstance(state.get("visible_objects", ()), (tuple, list)) else (),
            "environment_description": state.get("environment_description", "")
                if isinstance(state.get("environment_description", ""), str) else "",
        }
        return MappingProxyType(result)
