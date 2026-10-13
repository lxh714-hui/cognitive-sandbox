from __future__ import annotations

from cognitive_sandbox.application.npc.npc_action import NpcAction
from cognitive_sandbox.relationship.relationship_state import RelationshipState
from cognitive_sandbox.emotion.emotional_state import EmotionalState
from cognitive_sandbox.emotion.emotion_model import EmotionModel


class NpcDecisionEngine:
    """Generate deterministic response candidates from the NPC's own state."""

    def decide(self, character_mind, knowledge_context, world_event, relationships=(), *, npc_context=None, history=(),
               emotional_state: EmotionalState | None = None, emotional_memories=(), emotion_model=None,
               thought_pattern=None, cognitive_style=None):
        actor_id = _character_id(character_mind, knowledge_context, npc_context)
        role = _role(character_mind, npc_context).casefold()
        knowledge_records = tuple(getattr(knowledge_context, "records", ()))
        # Knowledge is deliberately scoped: records owned by another character
        # are ignored even if a caller supplied a malformed context.
        if any(getattr(record, "owner_id", actor_id) != actor_id for record in knowledge_records):
            knowledge_records = tuple(record for record in knowledge_records if getattr(record, "owner_id", None) == actor_id)
        event_type = world_event.event_type.casefold()
        target = getattr(world_event, "actor_id", None)
        if event_type in {"weapon_drawn", "weapon_draw", "weapon_threat", "weapon_fired"}:
            if _is_security_role(role, character_mind):
                prior_incidents = sum(
                    1 for record in history
                    if getattr(record, "event_type", "").casefold() in {"weapon_drawn", "weapon_draw", "weapon_threat", "weapon_fired"}
                    and target in (*getattr(record, "actor_ids", ()), *getattr(record, "target_ids", ()))
                    and getattr(record, "event_id", None) != world_event.event_id
                )
                responses = _security_responses(actor_id, target, world_event, relationships or (), prior_incidents)
                if emotional_state is None:
                    return responses
                emotion_model = emotion_model or EmotionModel()
                scores = {"warn": .6, "approach": .5, "ignore": .1, "ask": .65, "restrain": .7}
                ranked = [(scores.get(item.action_type, .2)
                           + emotion_model.score_modifier(item.action_type, emotional_state, emotional_memories)
                           + _cognitive_modifier(item.action_type, thought_pattern, cognitive_style), item)
                          for item in responses]
                for action_type, score in emotion_model.threshold_actions(emotional_state):
                    if action_type not in {item.action_type for _, item in ranked}:
                        ranked.append((score, NpcAction(actor_id, action_type, target,
                                                       {"source_event_id": world_event.event_id},
                                                       "情绪提高了该候选行动的倾向，但不强制执行。")))
                ranked.sort(key=lambda pair: (-pair[0], pair[1].action_type))
                weights = [__import__("math").exp(max(-20.0, min(20.0, score - ranked[0][0])))
                           for score, _ in ranked]
                denominator = sum(weights) or 1.0
                return tuple(NpcAction(item.actor_id, item.action_type, item.target,
                                       {**dict(item.parameters), "action_probability": weights[index] / denominator}, item.reason)
                             for index, (_, item) in enumerate(ranked))
            return (NpcAction(actor_id, "ignore", target, {"source_event_id": world_event.event_id}, "当前角色没有明显介入理由。"),)

        if getattr(world_event, "target_id", None) == actor_id:
            if any(token in event_type for token in ("help", "protect", "dialogue")):
                return (NpcAction(actor_id, "respond", target, {"source_event_id": world_event.event_id}, "事件直接涉及该角色。"),)
        if _knowledge_mentions_event(knowledge_context, knowledge_records, world_event):
            return (NpcAction(actor_id, "respond", target, {"source_event_id": world_event.event_id}, "角色依据自己掌握的信息作出回应。"),)
        return ()

    def decide_candidates(
        self, character_mind, knowledge_context, world_event, relationships=(), *,
        goals=(), motivation=None, risk=0.5, pressure=0.0, current_location=None,
        emotional_state: EmotionalState | None = None, emotional_memories=(), emotion_model=None,
        thought_pattern=None, cognitive_style=None,
    ):
        """Return ranked deterministic candidates without executing or committing them.

        This additive API combines the same scoped knowledge boundary as ``decide``
        with public goals, viewer-safe motives, relationship signals and pressure.
        The legacy ``decide`` API and its established security behavior remain intact.
        """
        actor_id = _character_id(character_mind, knowledge_context, None)
        if not 0 <= risk <= 1 or not 0 <= pressure <= 1:
            raise ValueError("risk and pressure must be between 0 and 1.")
        if emotional_state is not None and not isinstance(emotional_state, EmotionalState):
            raise TypeError("emotional_state must be EmotionalState or None.")
        emotion_model = emotion_model or EmotionModel()
        goals = tuple(goal for goal in goals if getattr(goal, "owner_id", actor_id) == actor_id
                      and getattr(goal, "status", "active") == "active")
        if any(getattr(record, "owner_id", actor_id) != actor_id
               for record in tuple(getattr(knowledge_context, "records", ()))):
            raise ValueError("decision knowledge must be scoped to this NPC.")
        event_type = str(getattr(world_event, "event_type", "")).casefold()
        description = " ".join((event_type, str(getattr(world_event, "payload", {})))).casefold()
        traits = tuple(str(value).casefold() for value in getattr(getattr(character_mind, "personality", None), "traits", ()))
        values = tuple(str(value).casefold() for value in getattr(getattr(character_mind, "personality", None), "values", ()))
        motive_view = motivation
        if motivation is not None and callable(getattr(motivation, "view_for", None)):
            motive_view = motivation.view_for(actor_id)
        motive_text = " ".join(str(getattr(motive_view, field, "") or "")
                               for field in ("public_goal", "hidden_goal", "core_drive", "fear", "value_conflict")).casefold()
        goal_text = " ".join(f"{getattr(goal, 'goal_type', '')} {getattr(goal, 'description', '')}" for goal in goals).casefold()
        relation = next((item for item in reversed(tuple(relationships))
                         if getattr(item, "source_id", None) == actor_id
                         and getattr(item, "target_id", None) == getattr(world_event, "actor_id", None)), None)
        relation_trust = float(getattr(relation, "trust", 0.0))
        candidates = []

        def add(action_type, score, reason):
            score += min(0.15, pressure * 0.15)
            if emotional_state is not None:
                score += emotion_model.score_modifier(action_type, emotional_state, emotional_memories)
            score += _cognitive_modifier(action_type, thought_pattern, cognitive_style)
            candidates.append((score, NpcAction(actor_id, action_type, getattr(world_event, "actor_id", None),
                                                {"source_event_id": world_event.event_id,
                                                 "location": current_location,
                                                 "risk": risk,
                                                 "decision_score": score}, reason)))

        abnormal = any(token in description for token in ("anomaly", "abnormal", "unknown", "异常", "调查", "secret", "秘密"))
        danger = any(token in description for token in ("danger", "attack", "weapon", "fire", "危险", "攻击", "武器", "火灾"))
        goal_investigate = any(token in goal_text or token in motive_text for token in ("investigate", "truth", "调查", "真相"))
        goal_protect = any(token in goal_text or token in motive_text or token in values for token in ("protect", "help", "保护", "守护", "帮助"))
        brave = any(token in " ".join((*traits, *values)) for token in ("brave", "courage", "勇敢", "无畏"))
        cautious = any(token in " ".join((*traits, *values)) for token in ("cautious", "careful", "谨慎", "保守"))

        if abnormal:
            add("investigate", 0.55 + (0.25 if goal_investigate else 0.0) + pressure * 0.1,
                "调查目标与当前异常相符。" if goal_investigate else "异常信息值得谨慎核实。")
        if danger:
            add("escape", 0.25 + risk * 0.45 + (0.2 if cautious else 0.0), "风险评估倾向于先拉开距离。")
            add("protect", 0.35 + (0.25 if goal_protect else 0.0) + (0.15 if brave else 0.0)
                + (0.05 if relation_trust > 0 else 0.0), "保护目标或关系对象符合当前职责。")
        if emotional_state is not None:
            if abnormal or danger or related_event_hint(event_type):
                for action_type, threshold_score in emotion_model.threshold_actions(emotional_state):
                    add(action_type, threshold_score, "极端情绪提高了该候选行动的倾向，但不强制执行。")
        related_event = (
            abnormal or danger
            or any(token in description for token in ("help", "protect", "dialogue", "inspect", "broken", "救助", "保护", "对话", "检查", "破碎"))
            or _knowledge_mentions_event(knowledge_context, tuple(getattr(knowledge_context, "records", ())), world_event)
        )
        if not candidates and related_event:
            add("observe", 0.5 + (0.1 if cautious else 0.0), "先观察以降低信息不确定性。")
        candidates.sort(key=lambda pair: (-pair[0], pair[1].action_type))
        # Convert deterministic scores to relative action probabilities for inspection/selection.
        weights = [__import__("math").exp(max(-20.0, min(20.0, score - candidates[0][0]))) for score, _ in candidates]
        denominator = sum(weights) or 1.0
        return tuple(
            NpcAction(action.actor_id, action.action_type, action.target,
                      {**dict(action.parameters), "action_probability": weights[index] / denominator}, action.reason)
            for index, (_, action) in enumerate(candidates)
        )


def _character_id(mind, knowledge_context, context):
    identity = getattr(mind, "identity", None)
    value = getattr(identity, "character_id", None) or getattr(mind, "character_id", None)
    value = value or getattr(knowledge_context, "owner_id", None) or getattr(context, "character_id", None)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("CharacterMind or npc_context must identify the NPC.")
    return value


def _role(mind, context):
    identity = getattr(mind, "identity", None)
    return str(getattr(identity, "role", None) or getattr(getattr(context, "character_state", None), "role", ""))


def _is_security_role(role, mind=None):
    if any(token in role for token in ("soldier", "guard", "security", "士兵", "守卫", "警卫")):
        return True
    traits = getattr(getattr(mind, "personality", None), "traits", ())
    values = (*traits, *getattr(getattr(mind, "personality", None), "values", ()))
    return any(
        token in str(value).casefold()
        for value in values
        for token in ("protect", "brave", "dutiful", "security", "警觉", "勇敢", "守护", "纪律")
    )


def _security_responses(actor_id, target, event, relationships, prior_incidents=0):
    params = {"source_event_id": event.event_id}
    current = next((
        relation for relation in reversed(tuple(relationships))
        if getattr(relation, "source_id", None) == actor_id
        and getattr(relation, "target_id", None) == target
    ), None)
    trust = getattr(current, "trust", 0.0)
    hostility = getattr(current, "hostility", 0.0)
    reason = "作为负责安全的角色，对武器威胁作出警戒反应。"
    ordinary = (
        NpcAction(actor_id, "warn", target, params, reason),
        NpcAction(actor_id, "approach", target, params, "靠近现场确认威胁。"),
        NpcAction(actor_id, "ignore", target, params, "不介入当前情况。"),
    )
    if isinstance(current, RelationshipState) and (hostility >= 50 or trust <= -50):
        return (
            NpcAction(actor_id, "restrain", target, params, "敌对关系使角色选择控制持武者。"),
            ordinary[0], ordinary[2],
        )
    if isinstance(current, RelationshipState) and trust >= 50:
        return (
            NpcAction(actor_id, "ask", target, params, "较高信任使角色先询问对方意图。"),
            ordinary[0], ordinary[2],
        )
    if prior_incidents > 0:
        return (ordinary[1], ordinary[0], ordinary[2])
    # Keep the previous 0..1 relationship scale working for existing callers.
    if current is not None and not isinstance(current, RelationshipState) and trust < 0.3:
        return (ordinary[1], ordinary[0], ordinary[2])
    return ordinary


def _knowledge_mentions_event(knowledge_context, records, event):
    event_id = getattr(event, "event_id", "").casefold()
    event_type = getattr(event, "event_type", "").replace("_", " ").casefold()
    candidates = list(getattr(knowledge_context, "available_information", ()))
    candidates.extend(getattr(record, "known_content", "") for record in records)
    return any(
        isinstance(text, str)
        and (event_id in text.casefold() or event_type in text.casefold() or event_type.replace(" ", "") in text.casefold())
        for text in candidates
    )


def related_event_hint(event_type):
    return any(token in event_type for token in ("help", "protect", "dialogue", "inspect", "broken", "injured",
                                                  "救助", "保护", "对话", "检查", "受伤"))


def _cognitive_modifier(action_type, thought_pattern, cognitive_style):
    """Small deterministic preference based on the character's current interpretation."""
    if thought_pattern is None:
        return 0.0
    interpretation = str(getattr(thought_pattern, "interpretation", ""))
    focus = " ".join(getattr(thought_pattern, "observation_focus", ()))
    score = 0.0
    if action_type == "investigate" and any(term in interpretation + focus for term in ("异常", "核实", "调查", "线索")):
        score += .12
    if action_type == "escape" and "故障" in interpretation:
        score += .18
    if action_type == "protect" and any(term in interpretation for term in ("承受压力", "保护", "担心")):
        score += .12
    if action_type == "observe" and "尚未确定" in interpretation:
        score += .06
    if action_type == "escape" and cognitive_style is not None and cognitive_style.pragmatic >= .75:
        score += .04
    return score
