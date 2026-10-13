from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import replace
from uuid import uuid4

from cognitive_sandbox.application.npc.npc_decision_engine import NpcDecisionEngine
from cognitive_sandbox.application.npc.npc_event_filter import NpcEventFilter
from cognitive_sandbox.domain.character_mind import KnowledgeContext
from cognitive_sandbox.domain.world_events import WorldEvent


class NpcResponseService:
    """Filter affected NPCs and record their first deterministic response candidate."""

    _DESCRIPTIONS = {
        "warn": "附近的士兵提高警惕，出声警告。",
        "approach": "附近的士兵朝事发地点靠近。",
        "ask": "士兵没有立即动手，而是先询问你的意图。",
        "restrain": "敌对的士兵试图控制持武者。",
        "respond": "角色对涉及自己的情况作出回应。",
        "ignore": "角色没有介入这件事。",
    }

    def __init__(self, event_filter=None, decision_engine=None, *, id_factory=None, clock=None):
        self.event_filter = event_filter or NpcEventFilter()
        self.decision_engine = decision_engine or NpcDecisionEngine()
        self._id_factory = id_factory or (lambda: uuid4().hex)
        self._clock = clock or (lambda: datetime.now(timezone.utc).isoformat())

    def handle_event(self, event, agent_contexts=(), *, context=None):
        if not isinstance(agent_contexts, (tuple, list)):
            raise TypeError("agent_contexts must be a collection")
        if not isinstance(event, WorldEvent):
            raise TypeError("event must be a WorldEvent")
        minds = getattr(context, "character_minds", None) or {}
        retriever = getattr(context, "knowledge_retriever", None)
        affected = self.event_filter.filter(
            event, agent_contexts, character_minds=minds, knowledge_retriever=retriever
        )
        presence_manager = getattr(context, "presence_manager", None)
        if presence_manager is not None:
            affected = tuple(agent for agent in affected
                             if getattr(getattr(getattr(presence_manager.get(agent.character_id), "availability", None), "value", None), "upper", lambda: "")()
                             in {"INTRODUCED", "ACTIVE"})
        responses = []
        for agent in affected:
            mind = minds.get(agent.character_id)
            knowledge = getattr(mind, "knowledge_context", None) or KnowledgeContext(owner_id=agent.character_id)
            manager = getattr(context, "relationship_manager", None)
            if manager is not None:
                relationships = manager.for_character(agent.character_id)
                if mind is not None:
                    from cognitive_sandbox.domain.character_mind import RelationshipContext

                    mind = replace(
                        mind,
                        relationship_context=RelationshipContext(agent.character_id, relationships),
                    )
                    minds[agent.character_id] = mind
            else:
                relationships = tuple(
                    relationship for relationship in getattr(mind, "relationship_context", ()).relationships
                ) if getattr(mind, "relationship_context", None) is not None else tuple(
                    relationship for relationship in getattr(agent, "relationships", ())
                    if relationship.source_id == agent.character_id or relationship.target_id == agent.character_id
                )
            history = (
                tuple(record for record in context.event_timeline.get_recent_events(100)
                      if record.event_id != event.event_id)
                if getattr(context, "event_timeline", None) is not None else ()
            )
            goal_manager = getattr(context, "goal_manager", None)
            motivation_manager = getattr(context, "motivation_manager", None)
            goals = tuple(goal_manager.for_character(agent.character_id)) if goal_manager is not None else ()
            motivation = motivation_manager.get_for_character(agent.character_id, agent.character_id) if motivation_manager is not None else None
            emotion_engine = getattr(context, "emotion_engine", None)
            emotional_state = (emotion_engine.states.get(agent.character_id)
                               if emotion_engine is not None else None)
            emotional_memories = (emotion_engine.memories_for(agent.character_id)
                                  if emotion_engine is not None else ())
            cognitive_engine = getattr(context, "cognitive_engine", None)
            thought = None
            cognitive_style = None
            if cognitive_engine is not None:
                visible = tuple(getattr(knowledge, "available_information", ())) + tuple(
                    record.known_content for record in getattr(knowledge, "records", ())
                    if isinstance(getattr(record, "known_content", None), str) and record.known_content.strip()
                )
                # The triggering event is not automatically disclosed; it must be
                # represented in this character's already scoped knowledge.
                if visible:
                    safe_event = _event_view_from_knowledge(event, visible)
                    if safe_event is not None:
                        thought = cognitive_engine.interpret_event(agent.character_id, safe_event, visible)
                        cognitive_style = cognitive_engine.style_for(agent.character_id)
            if event.event_type.casefold() in {"weapon_drawn", "weapon_draw", "weapon_threat", "weapon_fired"}:
                candidates = self.decision_engine.decide(mind, knowledge, event, relationships,
                                                         npc_context=agent, history=history,
                                                         emotional_state=emotional_state,
                                                         emotional_memories=emotional_memories,
                                                         thought_pattern=thought,
                                                         cognitive_style=cognitive_style)
            elif goal_manager is not None or motivation is not None:
                candidates = self.decision_engine.decide_candidates(
                    mind, knowledge, event, relationships, goals=goals, motivation=motivation,
                    risk=getattr(agent, "risk_level", 0.5), pressure=getattr(context, "narrative_pressure", None).urgency
                    if getattr(context, "narrative_pressure", None) is not None else 0.0,
                    current_location=getattr(event, "location", None),
                    emotional_state=emotional_state,
                    emotional_memories=emotional_memories,
                    thought_pattern=thought,
                    cognitive_style=cognitive_style,
                )
            else:
                candidates = self.decision_engine.decide(mind, knowledge, event, relationships,
                                                         npc_context=agent, history=history,
                                                         thought_pattern=thought,
                                                         cognitive_style=cognitive_style)
            action = next((candidate for candidate in candidates if candidate.action_type != "ignore"), None)
            if action is None:
                continue
            description = self._DESCRIPTIONS.get(action.action_type, "角色对眼前的情况作出回应。")
            responses.append(WorldEvent(
                event_id=f"npc_event_{self._id_factory()}",
                branch_id=event.branch_id,
                world_id=event.world_id,
                event_type=f"npc_{action.action_type}",
                actor_id=action.actor_id,
                payload={
                    "source_event_id": event.event_id,
                    "target_id": action.target,
                    "action_type": action.action_type,
                    "reason": action.reason,
                    "description": description,
                    "actor_name": getattr(getattr(mind, "identity", None), "name", None)
                    or agent.character_state.name,
                },
                world_revision=event.world_revision,
                target_id=action.target,
                location=event.location,
                timestamp=event.timestamp or self._clock(),
                metadata={"source_event_id": event.event_id},
            ))
        return tuple(responses)

    def handle_event_with_context(self, event, context):
        """Runtime hook that receives the already assembled, scoped turn context."""
        return self.handle_event(event, context.agent_contexts, context=context)


def _event_view_from_knowledge(event, visible):
    """Expose a triggering event only when its type is present in scoped knowledge."""
    event_type = event.event_type.replace("_", " ").casefold()
    if not any(event_type in item.casefold() or event.event_id.casefold() in item.casefold()
               for item in visible if isinstance(item, str)):
        return None
    return event
