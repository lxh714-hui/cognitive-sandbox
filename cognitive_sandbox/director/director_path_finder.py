from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DirectorPath:
    title: str
    steps: tuple[str, ...]
    score: float
    rationale: str
    conditions: tuple[str, ...] = ()
    thread_ids: tuple[str, ...] = ()
    constraint_score: float = 0.0

    def __post_init__(self):
        for key in ("title", "rationale"):
            if not isinstance(getattr(self, key), str) or not getattr(self, key).strip():
                raise ValueError(f"{key} must not be empty.")
        for key in ("steps", "conditions", "thread_ids"):
            values = tuple(getattr(self, key))
            if any(not isinstance(item, str) or not item.strip() for item in values):
                raise ValueError(f"{key} must contain non-empty strings.")
            object.__setattr__(self, key, values)
        if isinstance(self.score, bool) or not isinstance(self.score, (int, float)) or not 0 <= self.score <= 1:
            raise ValueError("score must be between 0 and 1.")
        object.__setattr__(self, "score", float(self.score))
        if not -1 <= self.constraint_score <= 1:
            raise ValueError("constraint_score must be between -1 and 1.")


class DirectorPathFinder:
    """Create explainable, non-binding routes from public runtime state only."""

    def __init__(self, constraint_evaluator=None):
        from .constraint_evaluator import DirectorConstraintEvaluator
        self.constraint_evaluator = constraint_evaluator or DirectorConstraintEvaluator()

    def find_paths(self, intent, *, world_state=None, presences=(), threads=(), goals=(),
                   relationships=(), emotions=None, candidate_events=(), maximum=3, constraints=()):
        world_state = world_state or {}
        presences, threads, goals = tuple(presences), tuple(threads), tuple(goals)
        target_ids = tuple(item for item in (intent.target or "").split(",") if item)
        by_id = {item.character_id: item for item in presences}
        relation_bias = _relation_bias(relationships, target_ids)
        emotion_penalty = _emotion_penalty(emotions, target_ids)
        goal_text = " ".join(
            f"{getattr(goal, 'description', '')} {getattr(goal, 'goal_type', '')}"
            for goal in goals
        ).casefold()
        goal_match = any(token in goal_text for token in ("调查", "investigate", "meet", "相遇", "线索", "help", "帮助"))
        paths = []
        kind = getattr(intent.intent_type, "value", intent.intent_type)
        if kind == "CHARACTER_ENTRY":
            for target_id in target_ids or (None,):
                presence = by_id.get(target_id)
                if presence is not None and getattr(presence.availability, "value", presence.availability) in {"UNKNOWN", "LEFT"}:
                    paths.append(DirectorPath(
                        "遵循角色入场条件",
                        ("等待角色自身的入场条件满足", "由相关目标或线索触发可解释的抵达", "在世界事件确认后加入当前场景"),
                        _clamp(.72 + (0.04 if goal_match else 0) - emotion_penalty), "不会提前登场；路径依赖角色既有入场规则和实际事件。",
                        ("entry_conditions_satisfied", "no_teleportation"),
                    ))
                paths.append(DirectorPath(
                    "通过剧情线索引出角色",
                    ("Event Planner 评估相关冲突", "生成可验证的线索候选", "角色依据自身目标决定是否介入"),
                    _clamp(.55 + (0.04 if goal_match else 0) - emotion_penalty), "角色是否出现仍由目标、位置和世界条件决定。",
                    ("planner_candidate_required", "character_agency_preserved"),
                ))
        elif kind == "CHARACTER_MEETING":
            locations = tuple(by_id[item].current_location for item in target_ids
                              if item in by_id and by_id[item].current_location)
            if len(set(locations)) > 1:
                steps = ("产生与双方目标相关的线索", "角色按自身目标前往可达地点", "在共同地点形成相遇机会")
                conditions = ("causal_travel_required", "reachable_location_required")
            else:
                steps = ("利用共同目标或未解线程形成交集", "由 Event Planner 产生相遇机会")
                conditions = ("shared_goal_or_thread_required", "no_teleportation")
            paths.append(DirectorPath("由共同目标促成相遇", steps,
                                       _clamp(.62 + relation_bias + (.06 if goal_match else 0) - emotion_penalty),
                                       "相遇只作为候选方向，角色位置和自主目标仍有效。", conditions))
            paths.append(DirectorPath("通过可达地点的偶发事件相遇",
                                       ("选择双方可以抵达的地点", "生成符合当前位置的事件候选", "由事件系统确认是否相遇"),
                                       _clamp(.48 + relation_bias * .5 - emotion_penalty), "不改变角色位置，也不预先确定事件结果。",
                                       ("reachable_location_required", "event_validation_required")))
            for thread in threads:
                if target_ids and set(target_ids).issubset(set(thread.participants)):
                    paths.append(DirectorPath(
                        "沿共享剧情线程形成交集",
                        (f"推进线程“{thread.title}”中的未解冲突", "由相关角色目标触发可达地点候选", "等待世界事件确认相遇机会"),
                        _clamp(.58 + thread.pressure * .15 + relation_bias - emotion_penalty),
                        "路径使用现有线程、关系和当前情绪评估可行性，不读取隐藏知识。",
                        ("shared_thread_required", "causal_travel_required"), (thread.id,),
                    ))
        elif kind in {"THREAD_PROGRESS", "WORLD_TENSION", "RELATIONSHIP_DEVELOPMENT"}:
            relevant = tuple(thread for thread in threads if not target_ids or set(target_ids) & set(thread.participants))
            if relevant:
                thread = relevant[0]
                paths.append(DirectorPath("沿现有剧情线程推进",
                                           (f"检查线程“{thread.title}”的未解冲突", "由相关目标产生事件候选", "根据事件结果更新线程进度"),
                                           min(1.0, .62 + thread.pressure * .2),
                                           "候选依赖已有线程冲突，不会直接改写线程结果。",
                                           ("thread_conflict_remains",), (thread.id,)))
        for candidate in candidate_events:
            if not target_ids or set(target_ids) & set(candidate.participants):
                paths.append(DirectorPath("复用已规划事件候选",
                                           (candidate.event_type, "通过既有事件验证和演化流程"),
                                           min(1.0, candidate.pressure), candidate.rationale,
                                           candidate.conditions, candidate.source_conflicts))
        if not paths:
            danger = world_state.get("danger_level", 0) if hasattr(world_state, "get") else 0
            score = min(.8, .45 + float(danger or 0) * .15 + intent.priority * .1)
            paths.append(DirectorPath("从当前目标寻找因果机会",
                                       ("检查公开目标与当前局势", "交由 Event Planner 提出条件化候选", "等待世界规则确认"),
                                       score, "路径仅使用公开世界状态、目标和已存在的剧情线程。",
                                       ("world_rules_apply", "no_direct_world_event")))
        unique = {}
        for path in paths:
            path_text = " ".join((path.title, *path.steps, path.rationale, *path.conditions))
            allowed, adjustment, _ = self.constraint_evaluator.score_path(
                path_text, constraints, candidate_id=path.title
            )
            if not allowed:
                continue
            path = DirectorPath(path.title, path.steps, _clamp(path.score + adjustment), path.rationale,
                                path.conditions, path.thread_ids, adjustment)
            unique[(path.title, path.steps, path.thread_ids)] = path
        return tuple(sorted(unique.values(), key=lambda path: (-path.score, path.title))[:max(0, maximum)])


def _clamp(value):
    return max(0.0, min(1.0, float(value)))


def _relation_bias(relationships, target_ids):
    if len(target_ids) < 2:
        return 0.0
    left, right = target_ids[:2]
    relation = next((item for item in relationships if
                     (item.source_id == left and item.target_id == right)
                     or (item.source_id == right and item.target_id == left)), None)
    if relation is None:
        return 0.0
    trust = float(getattr(relation, "trust", 0.0))
    affinity = float(getattr(relation, "affinity", 0.0))
    scale = 100 if abs(trust) > 1 or abs(affinity) > 1 else 1
    return max(-.12, min(.12, (trust + affinity) / scale * .06))


def _emotion_penalty(emotions, target_ids):
    if emotions is None:
        return 0.0
    penalty = 0.0
    state_for = getattr(emotions, "state_for", None)
    if not callable(state_for):
        return penalty
    for character_id in target_ids:
        state = state_for(character_id)
        penalty = max(penalty, min(.15, (state.fear + state.stress) * .075))
    return penalty
