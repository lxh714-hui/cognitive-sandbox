from __future__ import annotations

from dataclasses import replace
from collections.abc import Mapping

from .encounter_candidate import EncounterCandidate, EncounterStatus
from .encounter_condition import (
    CognitionCondition, EmotionCondition, GoalCondition, RelationshipCondition,
)


class EncounterEvaluator:
    """Deterministic, bilateral encounter assessment using only supplied character state."""

    MIN_AVAILABLE_SCORE = .45
    MIN_WILLINGNESS = .35

    def evaluate(self, candidate: EncounterCandidate, *, goals_a=(), goals_b=(),
                 relationship_a=None, relationship_b=None, stage_a="UNKNOWN", stage_b="UNKNOWN",
                 emotion_a=None, emotion_b=None, cognition_a=None, cognition_b=None,
                 social_density=0.0, narrative_pressure=0.0) -> EncounterCandidate:
        if not isinstance(candidate, EncounterCandidate):
            raise TypeError("candidate must be EncounterCandidate.")
        conditions = list(candidate.conditions)
        structural = [item.passed for item in conditions]
        willingness_a = self._willingness(candidate.activity_a, goals_a, emotion_a, cognition_a)
        willingness_b = self._willingness(candidate.activity_b, goals_b, emotion_b, cognition_b)
        hostility = max(_relationship_value(relationship_a, "hostility"),
                        _relationship_value(relationship_b, "hostility"))
        relation_ok = hostility < 80 and stage_a != "BROKEN" and stage_b != "BROKEN"
        goal_a, goal_b = _goal_text(goals_a), _goal_text(goals_b)
        aligned_goals = _goal_alignment(candidate.activity_a, goal_a) + _goal_alignment(candidate.activity_b, goal_b)
        conditions.extend((
            GoalCondition(goal_a, goal_b, True,
                          "目标倾向支持接触" if aligned_goals else "目标未直接推动接触，仍可因地点与行动相遇"),
            RelationshipCondition(str(getattr(stage_a, "value", stage_a)),
                                  str(getattr(stage_b, "value", stage_b)), hostility,
                                  relation_ok, "关系允许接触" if relation_ok else "严重敌意阻碍接触"),
            EmotionCondition(willingness_a, willingness_b,
                             willingness_a >= self.MIN_WILLINGNESS and willingness_b >= self.MIN_WILLINGNESS,
                             "双方都存在接触意愿" if min(willingness_a, willingness_b) >= self.MIN_WILLINGNESS
                             else "至少一方暂不愿接触"),
            CognitionCondition(_style_name(cognition_a), _style_name(cognition_b), True,
                               "认知风格只调整解释倾向"),
        ))
        location_ok = all(item.passed for item in conditions if item.__class__.__name__ == "LocationCondition")
        time_ok = all(item.passed for item in conditions if item.__class__.__name__ == "TimeCondition")
        score = .22 + (.18 if location_ok else 0) + (.12 if time_ok else 0)
        score += .10 * min(1.0, max(0.0, social_density))
        score += .06 * min(1.0, max(0.0, narrative_pressure))
        score += .18 * (willingness_a + willingness_b) / 2
        score += .04 * min(1, aligned_goals)
        score += .08 if _compatible(candidate.activity_a, candidate.activity_b) else 0
        score -= min(.24, hostility / 100 * .24)
        score = max(0.0, min(1.0, score))
        if not all(structural) or not relation_ok or min(willingness_a, willingness_b) < self.MIN_WILLINGNESS:
            status = EncounterStatus.REJECTED
        elif score >= self.MIN_AVAILABLE_SCORE:
            status = EncounterStatus.AVAILABLE
        else:
            status = EncounterStatus.POSSIBLE
        reason = "行动轨迹重合且双方愿意接触" if status is EncounterStatus.AVAILABLE else candidate.reason
        return replace(candidate, conditions=tuple(conditions), score=score, status=status,
                       willingness_a=willingness_a, willingness_b=willingness_b, reason=reason)

    @staticmethod
    def _willingness(activity, goals, emotion, cognition):
        text = str(activity).casefold()
        value = .48
        if any(word in text for word in ("talk", "social", "help", "protect", "交谈", "帮助", "保护")):
            value += .18
        elif any(word in text for word in ("investigate", "observe", "inspect", "调查", "观察", "查看")):
            value += .08
        elif any(word in text for word in ("avoid", "escape", "leave", "rest", "回避", "离开", "休息")):
            value -= .22
        value += .15 * _emotion_value(emotion, "curiosity")
        value += .05 * _emotion_value(emotion, "hope")
        value -= .22 * _emotion_value(emotion, "fear")
        value -= .24 * _emotion_value(emotion, "anger")
        value += min(.04, len(tuple(goals)) * .01)
        style = getattr(cognition, "style", None) or cognition
        if isinstance(cognition, Mapping):
            style = cognition.get("cognitive_style", cognition)
        value -= .06 * float(getattr(style, "suspicious", 0) or 0)
        return max(0.0, min(1.0, value))


def _emotion_value(state, name):
    try:
        return max(0.0, min(1.0, float(getattr(state, name, 0) or 0)))
    except (TypeError, ValueError):
        return 0.0


def _relationship_value(state, name):
    value = getattr(state, name, 0) if state is not None else 0
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(100.0, number * 100 if abs(number) <= 1 else number))


def _goal_text(goals):
    return "; ".join(str(getattr(item, "description", item)) for item in tuple(goals)[:3])


def _style_name(cognition):
    style = getattr(cognition, "style", None) or cognition
    if isinstance(style, Mapping):
        style = style.get("cognitive_style", style)
    if style is None:
        return ""
    return max(("analytical", "intuitive", "creative", "suspicious", "pragmatic", "emotional", "strategic"),
               key=lambda key: getattr(style, key, 0), default="")


def _compatible(first, second):
    words = ("talk", "social", "help", "protect", "investigate", "observe", "work", "travel",
             "交谈", "帮助", "保护", "调查", "观察", "工作", "出行")
    return any(word in str(first).casefold() for word in words) and any(
        word in str(second).casefold() for word in words
    )


def _goal_alignment(activity, goal_text):
    if not goal_text:
        return 0
    action = str(activity).casefold()
    goal = goal_text.casefold()
    groups = (
        (("investigate", "调查", "异常", "线索", "核实"), ("investigate", "调查", "异常", "线索", "核实")),
        (("social", "talk", "help", "protect", "交谈", "帮助", "保护"),
         ("关系", "合作", "帮助", "保护", "社交", "交谈")),
        (("work", "organize", "日常", "工作", "整理"), ("生活", "工作", "整理", "维持")),
        (("observe", "观察", "查看"), ("观察", "变化", "留意")),
    )
    return int(any(any(token in action for token in actions)
                   and any(token in goal for token in goals) for actions, goals in groups))


__all__ = ["EncounterEvaluator"]
