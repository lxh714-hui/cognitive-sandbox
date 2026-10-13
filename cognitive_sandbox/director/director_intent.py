from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from .constraint_type import ConstraintType
from .constraint_target import ConstraintTarget
from .constraint_strength import ConstraintStrength


class DirectorIntentType(str, Enum):
    CHARACTER_ENTRY = "CHARACTER_ENTRY"
    CHARACTER_MEETING = "CHARACTER_MEETING"
    RELATIONSHIP_DEVELOPMENT = "RELATIONSHIP_DEVELOPMENT"
    THREAD_PROGRESS = "THREAD_PROGRESS"
    WORLD_TENSION = "WORLD_TENSION"
    CUSTOM_DIRECTION = "CUSTOM_DIRECTION"


@dataclass(frozen=True)
class DirectorIntent:
    intent_type: DirectorIntentType
    target: str | None
    description: str
    priority: float = 0.5
    created_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    constraint_type: ConstraintType = ConstraintType.PREFER
    constraint_target: ConstraintTarget = ConstraintTarget.THEME
    category: str = "general"
    strength: ConstraintStrength = ConstraintStrength.MEDIUM

    def __post_init__(self):
        if not isinstance(self.intent_type, DirectorIntentType):
            object.__setattr__(self, "intent_type", DirectorIntentType(self.intent_type))
        if self.target is not None and (not isinstance(self.target, str) or not self.target.strip()):
            raise ValueError("target must be None or non-empty.")
        for key in ("description", "created_time"):
            if not isinstance(getattr(self, key), str) or not getattr(self, key).strip():
                raise ValueError(f"{key} must not be empty.")
        if isinstance(self.priority, bool) or not isinstance(self.priority, (int, float)) or not 0 <= self.priority <= 1:
            raise ValueError("priority must be between 0 and 1.")
        object.__setattr__(self, "priority", float(self.priority))
        if not isinstance(self.constraint_type, ConstraintType):
            object.__setattr__(self, "constraint_type", ConstraintType(self.constraint_type))
        if not isinstance(self.constraint_target, ConstraintTarget):
            object.__setattr__(self, "constraint_target", ConstraintTarget(self.constraint_target))
        if not isinstance(self.strength, ConstraintStrength):
            object.__setattr__(self, "strength", ConstraintStrength(self.strength))
        if not isinstance(self.category, str) or not self.category.strip():
            raise ValueError("category must not be empty.")


class DirectorIntentParser:
    """Deterministic language-to-direction parser; it never proposes outcomes."""

    KEYWORDS = (
        (DirectorIntentType.CHARACTER_MEETING, ("相遇", "见面", "碰面", "交汇")),
        (DirectorIntentType.CHARACTER_ENTRY, ("出现", "登场", "加入", "抵达")),
        (DirectorIntentType.RELATIONSHIP_DEVELOPMENT, ("关系", "信任", "亲近", "疏远")),
        (DirectorIntentType.THREAD_PROGRESS, ("调查", "线索", "线程", "推进")),
        (DirectorIntentType.WORLD_TENSION, ("危机", "冲突", "压力", "紧张")),
        (DirectorIntentType.CUSTOM_DIRECTION, ("异常", "希望", "引导", "发展")),
    )

    def parse(self, text: str, known_characters=()) -> DirectorIntent:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("director direction must not be empty.")
        raw = text.strip()
        constraint_type = ConstraintType.PREFER
        if any(word in raw for word in ("禁止", "绝不", "不允许", "不得")):
            constraint_type = ConstraintType.FORBID
        elif any(word in raw for word in ("避免", "我不要", "不希望")) or (
            "不要" in raw and any(word in raw for word in ("太早", "过早", "提前"))
        ):
            constraint_type = ConstraintType.AVOID
        elif "不要" in raw:
            constraint_type = ConstraintType.FORBID
        constraint_target, category = _constraint_subject(raw)
        kind = next((intent_type for intent_type, words in self.KEYWORDS
                     if any(word in raw for word in words)), DirectorIntentType.CUSTOM_DIRECTION)
        matches = []
        for item in known_characters:
            character_id, name = item if isinstance(item, tuple) else (item.character_id, item.character_state.name)
            if name and name in raw:
                matches.append((len(name), character_id))
            elif character_id and character_id.casefold() in raw.casefold():
                matches.append((len(character_id), character_id))
        target_ids = tuple(dict.fromkeys(value for _, value in sorted(matches, reverse=True)))
        target = ",".join(target_ids) if target_ids else None
        strength = ConstraintStrength.HIGH if constraint_type is ConstraintType.FORBID else ConstraintStrength.MEDIUM
        return DirectorIntent(kind, target, raw, .7, constraint_type=constraint_type,
                              constraint_target=constraint_target, category=category, strength=strength)


def _constraint_subject(text):
    if any(word in text for word in ("真相", "知道", "揭露", "揭开")):
        return ConstraintTarget.KNOWLEDGE_REVEAL, "truth_reveal"
    if any(word in text for word in ("死亡", "死去", "丧命")):
        return ConstraintTarget.EVENT, "death"
    if any(word in text for word in ("恋爱", "浪漫", "情侣")):
        return ConstraintTarget.RELATIONSHIP, "romance"
    if any(word in text for word in ("合作", "伙伴", "关系", "信任")):
        return ConstraintTarget.RELATIONSHIP, "cooperation"
    if any(word in text for word in ("结局", "结尾")):
        return ConstraintTarget.ENDING, "ending"
    if any(word in text for word in ("调查", "线程", "线索")):
        return ConstraintTarget.NARRATIVE_THREAD, "investigation"
    return ConstraintTarget.THEME, "general"
