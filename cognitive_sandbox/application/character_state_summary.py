from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CharacterStateSummary:
    character_id: str
    current_goal: str = ""
    current_stage: str = ""
    recent_change: str = ""
    goal_status: str = ""
    pressure_level: str = ""
    action_tendency: str = ""
    current_conflict: str = ""

    def __post_init__(self):
        if not isinstance(self.character_id, str) or not self.character_id.strip():
            raise ValueError("character_id must not be empty.")
        for field in ("current_goal", "current_stage", "recent_change", "goal_status", "pressure_level", "action_tendency", "current_conflict"):
            value = getattr(self, field)
            if not isinstance(value, str):
                raise TypeError(f"{field} must be a string.")


class CharacterStateSummaryBuilder:
    """Build a compact descriptive snapshot from already available runtime state."""

    def build(self, character_id, *, goals=(), emotion=None, cognition=None,
              relationships=(), information=(), recent_thoughts=(),
              goal_lifecycle=None, narrative_pressure=None, conflicts=()):
        if not isinstance(character_id, str) or not character_id.strip():
            raise ValueError("character_id must not be empty.")
        active = [goal for goal in goals if getattr(goal, "owner_id", None) == character_id
                  and getattr(goal, "status", "active") not in {"completed", "failed"}]
        active.sort(key=lambda item: (-float(getattr(item, "priority", 0)),
                                      -float(getattr(item, "progress", 0)), item.goal_id))
        current_goal = getattr(active[0], "description", "") if active else ""
        stage = _stage(emotion, cognition, relationships, recent_thoughts)
        lifecycle_state = goal_lifecycle.state_for(active[0].goal_id) if active and goal_lifecycle is not None else None
        stagnation = getattr(lifecycle_state, "stagnation_level", 0.0)
        if lifecycle_state is not None:
            if stagnation >= .3:
                stage = "目标推进停滞"
            elif getattr(lifecycle_state, "progress_velocity", 0.0) > .05:
                stage = "目标正在推进"
        pressure_value = max(
            float(getattr(narrative_pressure, "goal_stagnation", 0.0) or 0.0),
            float(stagnation or 0.0),
        )
        pressure_level = "高" if pressure_value >= .65 else "中等" if pressure_value >= .3 else "低"
        action_tendency = "寻找新的信息来源或方法" if stagnation >= .3 else "继续当前目标方法"
        goal_status = "调查停滞" if stagnation >= .3 else "正在推进" if lifecycle_state and lifecycle_state.progress_velocity > .05 else "按计划进行" if active else "无进行中目标"
        changes = []
        for thought in tuple(recent_thoughts)[-3:]:
            interpretation = getattr(thought, "interpretation", "")
            if isinstance(interpretation, str) and interpretation.strip():
                changes.append(interpretation.strip())
        if not changes:
            for item in tuple(information)[-1:]:
                content = getattr(item, "known_content", None) or getattr(item, "content", None)
                if isinstance(content, str) and content.strip():
                    changes.append(content.strip())
        own_conflict = next((item for item in conflicts if character_id in getattr(item, "participants", ())
                             and getattr(getattr(item, "status", None), "value", getattr(item, "status", ""))
                             in {"emerging", "active", "escalating", "stable", "escalated"}), None)
        conflict_text = ""
        if own_conflict is not None:
            kind = getattr(getattr(own_conflict, "conflict_type", None), "value", "")
            conflict_text = {
                "goal_conflict": "当前目标受到阻碍",
                "resource_conflict": "可用资源有限",
                "information_conflict": "相关信息掌握程度不同",
                "value_conflict": "对当前情况存在不同理解",
            }.get(kind, "当前存在尚未解决的阻碍")
        return CharacterStateSummary(character_id, current_goal, stage, changes[-1] if changes else "",
                                     goal_status, pressure_level, action_tendency, conflict_text)


def _stage(emotion, cognition, relationships, thoughts):
    recent = tuple(thoughts)
    if recent:
        interpretation = getattr(recent[-1], "interpretation", "")
        if isinstance(interpretation, str) and interpretation.strip():
            return "重新理解近期经历"
    if emotion is not None:
        stress = getattr(emotion, "stress", 0.0)
        curiosity = getattr(emotion, "curiosity", 0.0)
        if isinstance(stress, (int, float)) and stress >= .65:
            return "承受较大压力"
        if isinstance(curiosity, (int, float)) and curiosity >= .65:
            return "积极寻找线索"
    style = getattr(cognition, "cognitive_style", None)
    if isinstance(cognition, dict):
        style = cognition.get("cognitive_style", style)
    if style is not None and getattr(style, "suspicious", 0) >= .7:
        return "谨慎核实信息"
    if tuple(relationships):
        return "维持已有关系"
    return "按当前目标行动" if emotion is not None else "当前状态稳定"
