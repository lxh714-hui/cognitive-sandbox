from __future__ import annotations

from datetime import timedelta
import hashlib

from .narrative_opportunity import NarrativeOpportunity, OpportunitySourceType


class EventEmergenceEvaluator:
    """Derive opportunity candidates from supplied snapshots without mutating them."""

    def __init__(self, *, importance_threshold: float = 0.55, lifetime_hours: int = 72):
        if not 0 <= importance_threshold <= 1:
            raise ValueError("importance_threshold must be between 0 and 1.")
        if isinstance(lifetime_hours, bool) or not isinstance(lifetime_hours, int) or lifetime_hours < 1:
            raise ValueError("lifetime_hours must be a positive integer.")
        self.importance_threshold = float(importance_threshold)
        self.lifetime_hours = lifetime_hours

    def evaluate(self, *, world_time, active_conflicts=(), active_goals=(), goal_states=(),
                 location_states=(), information_network=None, information_by_character=None,
                 relationships=(), relationship_events=(), current_location=None,
                 visible_character_ids=(), world_state=None):
        now = _as_datetime(world_time)
        created = now.isoformat() if now else str(world_time or "")
        expiry = (now + timedelta(hours=self.lifetime_hours)).isoformat() if now else None
        candidates = []
        states = {getattr(item, "goal_id", None): item for item in goal_states}

        for goal in tuple(active_goals):
            state = states.get(getattr(goal, "goal_id", None))
            stagnation = max(float(getattr(state, "stagnation_level", 0.0)),
                             float(getattr(state, "frustration_level", 0.0)))
            if getattr(goal, "status", "active") != "active" or stagnation < self.importance_threshold:
                continue
            owner = getattr(goal, "owner_id", None)
            candidates.append(self._candidate(
                OpportunitySourceType.GOAL, f"goal:{goal.goal_id}", created, expiry,
                description="这个目标一段时间没有明显进展，或许可以换个信息来源或方法。",
                goal=goal.goal_id, character=owner, importance=max(goal.priority, stagnation), urgency=stagnation,
                actions=("寻找新的信息来源", "询问相关人物", "暂时搁置"), visibility="owner",
                visible=(owner,) if owner else (),
            ))

        for conflict in tuple(active_conflicts):
            severity = float(getattr(conflict, "pressure", getattr(conflict, "severity", 0.0)))
            if severity < self.importance_threshold:
                continue
            participants = tuple(getattr(conflict, "participants", ()))
            candidates.append(self._candidate(
                OpportunitySourceType.CONFLICT, f"conflict:{conflict.id}", created, expiry,
                description="一项尚未解决的分歧可能需要沟通、回避，或重新考虑处理方式。",
                conflict=conflict.id, importance=severity, urgency=severity,
                actions=("尝试沟通", "暂时回避", "寻找折中办法"), visibility="participants",
                visible=participants,
            ))

        for owner, records in (information_by_character or {}).items():
            eligible = []
            for record in tuple(records):
                content = _known_content(record)
                importance = _bounded(_record_value(record, "confidence", _record_value(record, "reliability", .6)))
                if content and importance >= self.importance_threshold:
                    eligible.append((record, content, importance))
            if eligible:
                record, content, importance = max(
                    eligible,
                    key=lambda item: (_record_value(item[0], "created_at", ""), item[2], _record_id(item[0], item[1])),
                )
                candidates.append(self._candidate(
                    OpportunitySourceType.INFORMATION, f"information:{owner}:{_record_id(record, content)}",
                    created, expiry, description="你掌握的一条线索或传闻，或许值得进一步核实。",
                    character=owner, importance=importance, urgency=.25,
                    actions=("核实这条信息", "询问相关人物", "暂时忽略"), visibility="owner",
                    visible=(owner,),
                ))

        for event in tuple(relationship_events):
            kind = str(getattr(getattr(event, "event_type", None), "value", getattr(event, "event_type", ""))).casefold()
            participants = tuple(value for value in (
                getattr(event, "character_a", None), getattr(event, "character_b", None),
                getattr(event, "source_id", None), getattr(event, "target_id", None),
            ) if isinstance(value, str) and value)
            if len(set(participants)) < 2 or not any(token in kind for token in ("help", "cooperate", "share", "encounter", "argue")):
                continue
            for owner in dict.fromkeys(participants):
                candidates.append(self._candidate(
                    OpportunitySourceType.RELATIONSHIP, f"relationship:{kind}:{':'.join(sorted(participants))}:{owner}",
                    created, expiry, description="最近的一次接触可能为继续交流留下了空间。",
                    character=owner, importance=.58, urgency=.2,
                    actions=("继续交流", "询问共同经历", "暂时保持距离"), visibility="participants",
                    visible=participants,
                ))

        # World/location opportunities rely only on explicitly supplied visible state.
        for location in tuple(location_states):
            location_id = getattr(location, "location_id", "")
            if not location_id or location_id != current_location:
                continue
            raw_safety = float(getattr(location, "safety", 100.0))
            safety = _bounded(raw_safety / 100.0 if raw_safety > 1 else raw_safety)
            status = str(getattr(location, "status", "")).casefold()
            if safety <= .35 or any(token in status for token in ("damaged", "unstable", "危急", "受损")):
                score = max(1.0 - safety, .58)
                candidates.append(self._candidate(
                    OpportunitySourceType.WORLD, f"world:location:{location_id}", created, expiry,
                    description="当前地点有一处明显状况，检查周围或寻找协助可能会有收获。",
                    character=None, importance=score, urgency=score,
                    actions=("查看周围", "寻找协助", "离开此处"), visibility="public",
                    visible=tuple(visible_character_ids),
                ))

        candidates = [item for item in candidates if item.importance >= self.importance_threshold]
        # Keep this output stable across equivalent state snapshots.
        return tuple(sorted(candidates, key=lambda item: (-item.importance, -item.urgency, item.opportunity_id)))

    def _candidate(self, source, key, created, expiry, *, description, goal=None, conflict=None,
                   character=None, importance, urgency, actions, visibility, visible):
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
        return NarrativeOpportunity(
            opportunity_id=f"opportunity_{digest}", source_type=source,
            related_goal=goal, related_conflict=conflict, related_character=character,
            visibility=visibility, urgency=_bounded(urgency), importance=_bounded(importance),
            possible_actions=actions, created_time=created, expiry=expiry, description=description,
            visible_character_ids=tuple(visible),
        )


def _as_datetime(value):
    if hasattr(value, "isoformat"):
        return value
    if isinstance(value, str) and value.strip():
        from datetime import datetime
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _bounded(value):
    return min(1.0, max(0.0, float(value)))


def _known_content(record):
    if isinstance(record, str):
        return record.strip()
    value = record.get("content", "") if hasattr(record, "get") else getattr(
        record, "known_content", getattr(record, "content", "")
    )
    return value.strip() if isinstance(value, str) else ""


def _record_id(record, content):
    value = record.get("fact_id", record.get("record_id", "")) if hasattr(record, "get") else getattr(
        record, "fact_id", getattr(record, "record_id", "")
    )
    return str(value or hashlib.sha1(content.encode("utf-8")).hexdigest()[:12])


def _record_value(record, key, default=None):
    return record.get(key, default) if hasattr(record, "get") else getattr(record, key, default)
