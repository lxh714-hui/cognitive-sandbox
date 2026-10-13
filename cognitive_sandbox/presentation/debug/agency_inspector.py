from __future__ import annotations

from dataclasses import dataclass

from cognitive_sandbox.knowledge.retrieval.knowledge_query import KnowledgeQuery


@dataclass(frozen=True)
class AgencyCandidateView:
    action_type: str
    target: str | None
    score: float
    reason: str


@dataclass(frozen=True)
class AgencyInspection:
    character_id: str
    initiative: float
    current_drive: str
    candidates: tuple[AgencyCandidateView, ...]
    recent_actions: tuple[str, ...]


class AgencyInspector:
    """Read-only view of a character's public goal and their scoped action candidates."""

    def inspect(self, session, character_id: str) -> AgencyInspection:
        scheduler = session.executor.npc_scheduler
        agency = scheduler.agency_manager.get(character_id) if scheduler and scheduler.agency_manager else None
        if agency is None:
            raise KeyError(character_id)
        goals = session.executor.goal_manager.for_character(character_id)
        goal = next((item for item in goals if item.status == "active"), None)
        retriever = session.executor.knowledge_retriever
        visible = retriever.retrieve(character_id, KnowledgeQuery(limit=1000)) if retriever else ()
        emotion_engine = session.executor.emotion_engine
        emotion = emotion_engine.states.get(character_id) if emotion_engine else None
        cognition_engine = session.executor.cognitive_engine
        cognition = cognition_engine.context_for(character_id) if cognition_engine else None
        motivation_manager = session.motivation_manager
        motivation = motivation_manager.get_for_character(character_id, character_id) if motivation_manager else None
        relationship_manager = session.executor.relationship_manager
        relationships = relationship_manager.for_character(character_id) if relationship_manager else ()
        mind = session.executor.character_minds.get(character_id)
        presence = session.presence_manager.get(character_id)
        candidates = ()
        if goal is not None and scheduler.goal_action_generator is not None:
            generated = scheduler.goal_action_generator.generate(
                goal, visible, relationships, emotion, cognition, character_id=character_id,
                current_location=getattr(presence, "current_location", None),
                motivation=motivation,
            )
            candidates = tuple(AgencyCandidateView(
                item.action.action_type, item.action.target, item.score, item.action.reason
            ) for item in generated)
        history = tuple(
            f"{action} · {when}" for owner, action, when in scheduler.agency_manager.snapshot().autonomous_action_history
            if owner == character_id
        )[-5:]
        drive = goal.description if goal is not None else "日常安排"
        # Deliberately omit private knowledge, hidden motives and raw world state.
        return AgencyInspection(character_id, agency.initiative, drive, candidates, history)
