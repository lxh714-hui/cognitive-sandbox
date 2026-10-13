from __future__ import annotations

from datetime import datetime, timezone
import re
from uuid import uuid4

from cognitive_sandbox.domain.narrative_event import NarrativeEvent
from cognitive_sandbox.domain.roleplay_result import RoleplayResult
from cognitive_sandbox.domain.simulation_result import SimulationTickResult
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.knowledge.models.knowledge_record import KnowledgeRecord, KnowledgeType
from cognitive_sandbox.knowledge.models.knowledge_source import KnowledgeSource
from cognitive_sandbox.knowledge.models.knowledge_visibility import KnowledgeVisibility
from cognitive_sandbox.knowledge.models.world_fact import WorldFact


class ObserveHandler:
    """Turn explicitly visible scene details into scoped player knowledge."""

    def __init__(self, *, id_factory=None, clock=None) -> None:
        self._id_factory = id_factory or (lambda: uuid4().hex)
        self._clock = clock or (lambda: datetime.now(timezone.utc).isoformat())

    def handle(self, action, context) -> RoleplayResult:
        state = context.world_state
        findings = []
        location = _safe_text(state.get("location"))
        if location:
            findings.append(f"你身处{location}。")
        environment = _safe_text(state.get("environment_description"))
        if environment:
            findings.append(environment)
        for item in _items(state.get("visible_objects")):
            name = _safe_text(item.get("name") if isinstance(item, dict) else item)
            description = _safe_text(item.get("description", "")) if isinstance(item, dict) else ""
            if name:
                findings.append(f"你注意到{name}{'：' + description if description else '。'}")
        names = _display_names(context)
        for item in _items(state.get("visible_characters", state.get("nearby_characters"))):
            if isinstance(item, dict):
                identifier = item.get("character_id", item.get("id"))
                name = _safe_text(item.get("name")) or names.get(str(identifier), "")
                description = _safe_text(item.get("description", ""))
            else:
                name = names.get(str(item), "")
                description = ""
            if name:
                findings.append(f"附近有{name}{'，' + description if description else '。'}")
        for item in _items(state.get("visible_events", state.get("current_events"))):
            text = _safe_text(item.get("description", item.get("name", "")) if isinstance(item, dict) else item)
            if text:
                findings.append(text)
        # Scenario cards describe content, but only initial events explicitly tied
        # to the player are visible without a corresponding state condition.
        if not findings and context.scenario_content is not None:
            world = context.scenario_content.world_document
            if world is not None and _safe_text(world.description):
                findings.append(world.description.strip())
        if not findings:
            findings.append("眼前暂时没有新的线索；远处的声响和周围人的举动仍在变化。")

        cognitive_engine = getattr(context, "cognitive_engine", None)
        if cognitive_engine is not None:
            # The observer receives only findings already selected as visible here.
            from types import SimpleNamespace
            event_stub = SimpleNamespace(event_id=f"perception_{context.turn.turn_id}", event_type="observe_action")
            findings = list(cognitive_engine.attend(context.agent_context.character_id, findings))
            if findings:
                cognitive_engine.interpret_event(context.agent_context.character_id, event_stub, findings)

        event_id = f"event_{self._id_factory()}"
        world_clock = getattr(context, "world_clock", None)
        event = WorldEvent(
            event_id, context.branch_id, context.world_id, "observe_action",
            action.actor_id,
            {"observations": tuple(findings), "observation_kind": "perception"},
            0,
            timestamp=world_clock.current_time().isoformat() if world_clock is not None else None,
        )
        self.record(context, action.actor_id, event, findings)
        narrative = NarrativeEvent(event_id, "观察周围", "\n".join(findings), ())
        snapshot = SimulationTickResult(state, context.agent_context, (event,))
        return RoleplayResult(context.turn.turn_id, True, (narrative,), (), snapshot)

    def record(self, context, owner_id, event, findings) -> None:
        store = context.knowledge_store
        if store is None:
            return
        facts, records = store.snapshot()
        known = {
            record.known_content
            for record in records
            if record.owner_id == owner_id and record.known_content
        }
        timestamp = (context.world_clock.current_time().isoformat()
                     if getattr(context, "world_clock", None) is not None else self._clock())
        for content in findings:
            if content in known:
                continue
            fact_id = f"fact_{self._id_factory()}"
            fact = WorldFact(
                fact_id, content, "observation", timestamp, (owner_id,), 0.4
            )
            store.add_fact(fact)
            store.add_knowledge(KnowledgeRecord(
                owner_id=owner_id,
                fact_id=fact_id,
                knowledge_type=KnowledgeType.OBSERVED,
                source=KnowledgeSource(event.event_id, "OBSERVATION", "玩家亲自观察", owner_id),
                confidence=0.9,
                created_at=timestamp,
                known_content=content,
                visibility=KnowledgeVisibility(),
            ))
            known.add(content)


def _items(value):
    return value if isinstance(value, (tuple, list, set, frozenset)) else ()


def _safe_text(value):
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if (
        not text
        or text.casefold() in {"none", "null"}
        or "%" in text
        or any(token in text.casefold() for token in ("world_revision", "information_level", "api_key"))
        or ("_" in text and not re.search(r"[\u4e00-\u9fff]", text))
    ):
        return ""
    return text


def _display_names(context):
    result = {}
    for card in getattr(context.scenario_content, "character_cards", ()):
        if card.name and card.character_id != card.name:
            result[card.character_id] = card.name
    for agent in context.agent_contexts:
        name = agent.character_state.name
        if name and name != agent.character_id:
            result[agent.character_id] = name
    return result
