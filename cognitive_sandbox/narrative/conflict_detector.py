from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Conflict:
    conflict_id: str
    conflict_type: str
    participants: tuple[str, ...]
    description: str
    sources: tuple[str, ...]
    pressure: float = 0.5

    def __post_init__(self):
        for field in ("conflict_id", "conflict_type", "description"):
            if not isinstance(getattr(self, field), str) or not getattr(self, field).strip():
                raise ValueError(f"{field} must not be empty.")
        for field in ("participants", "sources"):
            values = tuple(getattr(self, field))
            if any(not isinstance(value, str) or not value.strip() for value in values):
                raise ValueError(f"{field} must contain non-empty strings.")
            object.__setattr__(self, field, values)
        if not 0 <= self.pressure <= 1:
            raise ValueError("pressure must be between 0 and 1.")


class ConflictDetector:
    """Find deterministic, explainable goal/value/resource incompatibilities."""

    def detect(self, goals=(), motivations=(), resources=(), *, character_values=None):
        goals = tuple(goal for goal in goals if getattr(goal, "status", "active") == "active")
        motivations = tuple(motivations)
        conflicts = []
        for index, left in enumerate(goals):
            for right in goals[index + 1:]:
                if getattr(left, "owner_id", None) == getattr(right, "owner_id", None):
                    continue
                left_text = f"{left.goal_type} {left.description}".casefold()
                right_text = f"{right.goal_type} {right.description}".casefold()
                if _opposed_information(left_text, right_text):
                    conflicts.append(Conflict(
                        f"information:{left.goal_id}:{right.goal_id}", "information_conflict",
                        (left.owner_id, right.owner_id), f"{left.description} 与 {right.description} 目标相冲突。",
                        (left.goal_id, right.goal_id), min(1.0, 0.4 + left.priority * 0.3 + right.priority * 0.3),
                    ))
                elif _resource_conflict(left_text, right_text, resources):
                    conflicts.append(Conflict(
                        f"resource:{left.goal_id}:{right.goal_id}", "resource_conflict",
                        (left.owner_id, right.owner_id), f"{left.description} 与 {right.description} 争用有限资源。",
                        (left.goal_id, right.goal_id), 0.55,
                    ))
                elif _value_conflict(left_text, right_text):
                    conflicts.append(Conflict(
                        f"value:{left.goal_id}:{right.goal_id}", "value_conflict",
                        (left.owner_id, right.owner_id), f"{left.description} 与 {right.description} 存在价值或规则冲突。",
                        (left.goal_id, right.goal_id), 0.45,
                    ))
        # Layered motives can expose public-vs-hidden tension as a thread source without leaking its text.
        for motivation in motivations:
            if getattr(motivation, "public_goal", "") and getattr(motivation, "hidden_goal", "") and _opposed_information(
                f"{motivation.public_goal} {motivation.hidden_goal}", "隐藏 真相"
            ):
                conflicts.append(Conflict(
                    f"internal:{motivation.character_id}", "internal_conflict", (motivation.character_id,),
                    "角色的公开目标与深层动机存在张力。", (f"motivation:{motivation.character_id}",), 0.35,
                ))
        return tuple(conflicts)

    def generate_threads(self, conflicts=()):
        from cognitive_sandbox.narrative.narrative_thread import NarrativeThread, NarrativeThreadStatus

        return tuple(
            NarrativeThread(
                id=f"thread:{conflict.conflict_id}",
                title=_thread_title(conflict),
                participants=conflict.participants,
                conflict=conflict.description,
                pressure=conflict.pressure,
                status=NarrativeThreadStatus.ACTIVE,
                conflict_sources=conflict.sources,
            )
            for conflict in conflicts
        )


def _opposed_information(left, right):
    truth = any(word in left for word in ("truth", "真相", "investigate", "调查", "寻找"))
    conceal = any(word in right for word in ("hide", "conceal", "隐藏", "掩盖", "保密"))
    reverse = any(word in right for word in ("truth", "真相", "investigate", "调查", "寻找")) and any(
        word in left for word in ("hide", "conceal", "隐藏", "掩盖", "保密")
    )
    return truth and conceal or reverse


def _resource_conflict(left, right, resources):
    medicine = any(word in left for word in ("medicine", "药", "medical", "医疗")) and any(
        word in right for word in ("hoard", "stockpile", "囤", "占有", "药", "medicine")
    )
    available = any(getattr(resource, "quantity", 0) <= getattr(resource, "reserved", 0) for resource in resources)
    return medicine and (available or any(word in right for word in ("hoard", "stockpile", "囤")))


def _value_conflict(left, right):
    order = any(word in left for word in ("order", "protect_city", "秩序", "巡逻", "维护"))
    transgress = any(word in right for word in ("forbidden", "禁区", "investigate", "调查"))
    reverse = any(word in right for word in ("order", "protect_city", "秩序", "巡逻")) and any(
        word in left for word in ("forbidden", "禁区", "investigate", "调查")
    )
    return order and transgress or reverse


def _thread_title(conflict):
    labels = {
        "information_conflict": "信息冲突",
        "resource_conflict": "资源争夺",
        "value_conflict": "价值抉择",
        "internal_conflict": "内心张力",
    }
    participants = "与".join(conflict.participants)
    return f"{participants}的{labels.get(conflict.conflict_type, '未解冲突')}" if participants else labels.get(conflict.conflict_type, "未解冲突")
