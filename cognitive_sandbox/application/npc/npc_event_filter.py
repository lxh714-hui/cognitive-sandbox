from __future__ import annotations

from collections.abc import Mapping


class NpcEventFilter:
    """Select NPCs plausibly affected by an event using only scoped scene data."""

    _SECURITY_ROLES = ("soldier", "guard", "security", "士兵", "守卫", "警卫")
    _WEAPON_EVENTS = {"weapon_drawn", "weapon_draw", "weapon_threat", "weapon_fired"}

    def filter(self, event, agent_contexts, *, character_minds=None, knowledge_retriever=None):
        contexts = tuple(agent_contexts)
        minds = character_minds or {}
        result = []
        event_location = _event_location(event)
        visible_to = _visible_to(event)
        secret = _event_metadata(event).get("observable") is False

        for agent in contexts:
            character_id = getattr(agent, "character_id", None)
            if not character_id or character_id == getattr(event, "actor_id", None):
                continue
            if visible_to is not None and character_id not in visible_to:
                continue

            known = _knows_event(character_id, event, minds, knowledge_retriever, agent)
            if secret and not known:
                continue
            if event_location is not None and not _at_location(agent, event_location):
                if not known:
                    continue
            if not _is_relevant(agent, event, known):
                continue
            result.append(agent)
        return tuple(result)

    def affected_agents(self, event, agent_contexts, **kwargs):
        return self.filter(event, agent_contexts, **kwargs)


def _event_metadata(event):
    metadata = getattr(event, "metadata", None)
    return metadata if isinstance(metadata, Mapping) else {}


def _event_location(event):
    if getattr(event, "location", None):
        return event.location
    metadata = _event_metadata(event)
    payload = getattr(event, "payload", {})
    for mapping in (metadata, payload if isinstance(payload, Mapping) else {}):
        location = mapping.get("location")
        if isinstance(location, str) and location.strip():
            return location.strip()
    return None


def _visible_to(event):
    metadata = _event_metadata(event)
    payload = getattr(event, "payload", {})
    payload = payload if isinstance(payload, Mapping) else {}
    value = metadata.get("visible_to", payload.get("visible_to"))
    if value is None:
        return None
    if isinstance(value, str):
        return {value}
    try:
        return {str(item) for item in value}
    except TypeError:
        return set()


def _at_location(agent, location):
    state = getattr(agent, "world_state", {})
    if not isinstance(state, Mapping):
        return False
    agent_location = state.get("location", state.get("current_location"))
    if isinstance(agent_location, str):
        return agent_location.casefold() == location.casefold()
    # Optional coordinates support distance-aware scenarios without imposing a
    # position schema on WorldState.
    event_position = state.get("event_positions", {}).get(location) if isinstance(state.get("event_positions"), Mapping) else None
    position = state.get("position")
    if isinstance(position, (tuple, list)) and isinstance(event_position, (tuple, list)) and len(position) == len(event_position) == 2:
        try:
            return ((position[0] - event_position[0]) ** 2 + (position[1] - event_position[1]) ** 2) ** 0.5 <= 25
        except TypeError:
            return False
    return False


def _is_relevant(agent, event, known):
    character_id = agent.character_id
    target = getattr(event, "target_id", None)
    metadata = _event_metadata(event)
    payload = getattr(event, "payload", {})
    payload = payload if isinstance(payload, Mapping) else {}
    if character_id == target:
        return True
    related = metadata.get("related_entities", payload.get("related_entities", ()))
    if isinstance(related, str):
        related = (related,)
    if not isinstance(related, (tuple, list, set, frozenset)):
        related = ()
    if character_id in related:
        return True
    event_type = getattr(event, "event_type", "").casefold()
    if event_type in NpcEventFilter._WEAPON_EVENTS:
        role = getattr(getattr(agent, "character_state", None), "role", "").casefold()
        traits = getattr(getattr(agent, "character_state", None), "traits", ())
        return any(token in role for token in NpcEventFilter._SECURITY_ROLES) or any(
            "protect" in str(trait).casefold() or "警觉" in str(trait) for trait in traits
        ) or known
    return True


def _knows_event(character_id, event, minds, retriever, agent):
    mind = minds.get(character_id) if isinstance(minds, Mapping) else None
    knowledge = getattr(mind, "knowledge_context", None)
    records = getattr(knowledge, "records", ())
    event_id = getattr(event, "event_id", "")
    event_type = getattr(event, "event_type", "")
    if any(
        isinstance(item, str) and (event_id.casefold() in item.casefold() or event_type.casefold() in item.casefold())
        for item in getattr(knowledge, "available_information", ())
    ):
        return True
    for record in records:
        if record.owner_id == character_id and (record.fact_id == event_id or event_type.casefold() in record.known_content.casefold()):
            return True
    if retriever is None:
        return False
    try:
        records = retriever.retrieve(character_id, event_type, current_context={"location": _event_location(event) or ""})
    except (KeyError, TypeError, ValueError):
        return False
    return any(record.owner_id == character_id for record in records)
