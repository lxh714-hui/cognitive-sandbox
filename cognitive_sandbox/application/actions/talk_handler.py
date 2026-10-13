from __future__ import annotations

from uuid import uuid4

from cognitive_sandbox.domain.character_mind import KnowledgeContext
from cognitive_sandbox.domain.dialogue import DialogueLine
from cognitive_sandbox.domain.narrative_event import NarrativeEvent
from cognitive_sandbox.domain.roleplay_result import RoleplayResult
from cognitive_sandbox.domain.simulation_result import SimulationTickResult
from cognitive_sandbox.domain.world_events import WorldEvent


class TalkHandler:
    def __init__(self, *, id_factory=None) -> None:
        self._id_factory = id_factory or (lambda: uuid4().hex)

    def handle(self, action, context) -> RoleplayResult:
        target = self._find_target(action.target, context)
        if target is None or target.character_id == action.actor_id:
            return RoleplayResult(
                context.turn.turn_id, False, (), (),
                system_message="这个行动目前无法直接执行。请描述你想做什么，或者补充目标人物、地点或物品。",
            )
        unreachable = context.world_state.get("inaccessible_character_ids", ())
        if target.character_id in unreachable:
            return RoleplayResult(
                context.turn.turn_id, False, (), (),
                system_message="现在无法接触到这名角色。",
            )
        player_location = context.world_state.get("location")
        npc_location = target.world_state.get("location")
        if isinstance(player_location, str) and isinstance(npc_location, str) and player_location != npc_location:
            return RoleplayResult(
                context.turn.turn_id, False, (), (),
                system_message="这名角色目前不在你所在的地点。",
            )

        event_id = f"event_{self._id_factory()}"
        topic = action.parameters.get("topic")
        event = WorldEvent(
            event_id, context.branch_id, context.world_id, "dialogue_event",
            action.actor_id,
            {"target_id": target.character_id, "input": action.raw_input, "topic": topic},
            0,
            target_id=target.character_id,
            location=context.world_state.get("location") if isinstance(context.world_state.get("location"), str) else None,
            timestamp=(context.world_clock.current_time().isoformat()
                       if getattr(context, "world_clock", None) is not None else None),
            metadata={"topic": topic} if isinstance(topic, str) else {},
        )
        dialogue = None
        service = context.dialogue_service
        mind = (context.character_minds or {}).get(target.character_id)
        if mind is not None and context.relationship_manager is not None:
            from dataclasses import replace
            from cognitive_sandbox.domain.character_mind import RelationshipContext

            scoped_relationships = tuple(
                relation
                for relation in context.relationship_manager.for_character(target.character_id)
                if relation.target_id == context.agent_context.character_id
            )
            mind = replace(
                mind,
                relationship_context=RelationshipContext(target.character_id, scoped_relationships),
            )
        knowledge = None
        if context.knowledge_retriever is not None:
            records = context.knowledge_retriever.retrieve(
                target.character_id, action.raw_input,
                current_context=_safe_scene(context.world_state),
            )
            knowledge = KnowledgeContext(records=records, owner_id=target.character_id)
        if service is not None:
            generate = getattr(service, "generate_with_context", None)
            if callable(generate):
                emotion_engine = getattr(context, "emotion_engine", None)
                emotional_state = emotion_engine.state_for(target.character_id) if emotion_engine is not None else None
                cognitive_engine = getattr(context, "cognitive_engine", None)
                cognitive_context = None
                if cognitive_engine is not None:
                    visible = tuple(getattr(knowledge, "available_information", ())) + tuple(
                        record.known_content for record in getattr(knowledge, "records", ())
                        if isinstance(getattr(record, "known_content", None), str) and record.known_content.strip()
                    )
                    from types import SimpleNamespace
                    thought = cognitive_engine.interpret_event(
                        target.character_id,
                        SimpleNamespace(event_id=event.event_id, event_type="dialogue_event"),
                        (*visible, action.raw_input),
                    )
                    cognitive_context = cognitive_engine.context_for(target.character_id)
                    cognitive_context = {**dict(cognitive_context), "current_interpretation": thought}
                dialogue = generate(
                    target,
                    context.agent_context,
                    action.raw_input,
                    character_mind=mind,
                    knowledge_context=knowledge,
                    current_event=f"玩家向{target.character_state.name}发起交谈。",
                    current_scene=(context.narrative_context or _safe_scene(context.world_state)),
                    emotional_state=emotional_state,
                    cognitive_context=cognitive_context,
                    authority_context=(
                        context.authority_manager.ai_authority_context(target.character_id)
                        if context.authority_manager is not None else None
                    ),
                )
            else:
                dialogue = service.generate(target, context.agent_context, action.raw_input)
        lines = (dialogue,) if isinstance(dialogue, DialogueLine) else ()
        participants = (context.agent_context.character_id, target.character_id)
        narrative = NarrativeEvent(
            event_id, "交谈", f"你向{target.character_state.name}发起交谈。", participants
        )
        snapshot = SimulationTickResult(context.world_state, context.agent_context, (event,))
        return RoleplayResult(context.turn.turn_id, True, (narrative,), lines, snapshot)

    @staticmethod
    def _find_target(target_ref, context):
        if not isinstance(target_ref, str) or not target_ref.strip():
            return None
        wanted = target_ref.strip().casefold()
        for agent in context.agent_contexts:
            candidates = {agent.character_id.casefold(), agent.character_state.name.casefold(), agent.character_state.role.casefold()}
            for card in getattr(context.scenario_content, "character_cards", ()):
                if card.character_id == agent.character_id:
                    candidates.update((card.name.casefold(), (card.occupation or "").casefold()))
            candidates.discard("")
            if wanted in candidates:
                return agent
        return None


def _safe_scene(state):
    allowed = ("location", "time", "visible_characters", "visible_objects", "visible_events", "environment_description", "weather")
    return {key: state[key] for key in allowed if key in state}
