from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from cognitive_sandbox.application.npc.npc_action import NpcAction


@dataclass(frozen=True)
class GoalActionCandidate:
    action: NpcAction
    score: float
    source: str
    priority: float

    def __post_init__(self):
        if not isinstance(self.action, NpcAction):
            raise TypeError("action must be NpcAction.")
        for name in ("score", "priority"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1.")
            object.__setattr__(self, name, float(value))
        if self.source not in {"emergency", "goal", "routine"}:
            raise ValueError("source must be emergency, goal, or routine.")


class GoalActionGenerator:
    """Map a character's own goal and supplied visible context to objective candidates."""

    _SOURCES = {"goal": 1.0, "routine": .55, "emergency": 1.0}

    def generate(self, goal, visible_knowledge=(), relationships=(), emotion=None, cognition=None,
                 *, character_id=None, current_location=None, motivation=None):
        owner = character_id or getattr(goal, "owner_id", None)
        if not owner:
            raise ValueError("character_id is required when no goal owner is available.")
        knowledge = _visible_text(visible_knowledge)
        goal_text = " ".join((getattr(goal, "goal_type", ""), getattr(goal, "description", ""))).casefold()
        style = getattr(cognition, "cognitive_style", None)
        if style is None and isinstance(cognition, Mapping):
            style = cognition.get("cognitive_style")
        curiosity = _number(emotion, "curiosity", .5)
        suspicious = _number(style, "suspicious", .5)
        analytical = _number(style, "analytical", .5)
        public_goal = getattr(motivation, "public_goal", "") or ""
        motivation_bonus = .04 if public_goal and any(
            token in public_goal.casefold() for token in ("调查", "寻找", "生活", "观察", "保护", "帮助")
        ) else 0.0
        relationship_bonus = _social_trust(relationships, owner)
        joined = knowledge.casefold()
        has_anomaly = any(word in joined for word in ("异常", "线索", "时间记录", "停摆", "重复"))
        location = current_location or "neighborhood"
        result = []

        def add(action_type, target=None, params=None, reason="", score=.5):
            params = dict(params or {})
            params["goal_id"] = getattr(goal, "goal_id", "")
            params["goal_type"] = getattr(goal, "goal_type", "")
            result.append(GoalActionCandidate(
                NpcAction(owner, action_type, target=target, parameters=params, reason=reason),
                max(0.0, min(1.0, score + motivation_bonus + (relationship_bonus if action_type == "socialize" else 0.0))),
                "goal", getattr(goal, "priority", .5),
            ))

        investigation_goal = any(word in goal_text for word in ("调查", "异常", "线索", "investigat"))
        ordinary_goal = any(word in goal_text for word in ("重新开始", "正常生活", "生活", "工作", "help", "保护", "protect"))
        observation_goal = any(word in goal_text for word in ("观察", "变化", "watch", "observe"))

        if investigation_goal:
            if has_anomaly:
                add("investigate", params={"location": location}, reason="目标要求核实角色已知的线索",
                    score=.58 + .2 * curiosity + .12 * suspicious)
                add("organize", params={"topic": "visible_clues"}, reason="整理自己已经掌握的线索",
                    score=.48 + .16 * analytical)
                if any(word in joined for word in ("角色", "医生", "士兵", "商人", "居民")):
                    add("socialize", params={"topic": "visible_clues"}, reason="向相关人物询问已知线索",
                        score=.4 + .12 * curiosity)
                add("observe", params={"location": location}, reason="继续观察线索所在区域",
                    score=.42 + .15 * curiosity)
        elif observation_goal:
            add("observe", params={"location": location}, reason="持续观察周围变化",
                score=.48 + .15 * curiosity)
            add("organize", params={"topic": "observations"}, reason="整理近期观察记录",
                score=.4 + .12 * analytical)
            add("rest", reason="等待新的变化出现", score=.32)
        elif ordinary_goal:
            add("work", params={"location": current_location or "home"}, reason="维持日常生活", score=.5)
            add("organize", params={"location": current_location or "home"}, reason="整理生活环境", score=.43)
            add("socialize", params={"location": current_location or "neighborhood"}, reason="保持日常社交联系", score=.38)
            if has_anomaly and curiosity > .7 and suspicious > .65:
                add("investigate", params={"location": location}, reason="已知异常线索引起角色关注", score=.35)
        else:
            add("observe", params={"location": location}, reason="先观察当前环境", score=.42)
            add("rest", reason="暂时等待并保持警觉", score=.3)
        result.sort(key=lambda item: (-item.score, item.action.action_type, repr(item.action.parameters)))
        return tuple(result)


def _visible_text(values):
    if values is None:
        return ""
    if isinstance(values, str):
        return values
    parts = []
    for item in tuple(values):
        text = getattr(item, "known_content", None)
        if not isinstance(text, str):
            text = getattr(item, "content", item if isinstance(item, str) else "")
        if isinstance(text, str):
            parts.append(text)
    return " ".join(parts)


def _number(source, name, default):
    value = getattr(source, name, None)
    if value is None and isinstance(source, Mapping):
        value = source.get(name)
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else default


def _social_trust(relationships, owner):
    if relationships is None:
        return 0.0
    values = tuple(relationships)
    scores = []
    for relation in values:
        if getattr(relation, "source_id", None) != owner:
            continue
        trust = float(getattr(relation, "trust", 0.0))
        affinity = float(getattr(relation, "affinity", 0.0))
        if trust < 0:
            trust = (trust + 100) / 200
        if affinity < 0:
            affinity = (affinity + 100) / 200
        scores.append(max(0.0, min(1.0, (trust + affinity) / 2)) * .12)
    return max(scores, default=0.0)
