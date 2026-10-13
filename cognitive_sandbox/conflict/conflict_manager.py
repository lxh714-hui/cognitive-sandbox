from dataclasses import dataclass, replace
from datetime import datetime, timezone

from cognitive_sandbox.narrative.conflict_detector import ConflictDetector
from .conflict_state import (ConflictState, ConflictStatus, GoalPressure, ConflictParticipant,
                             ConflictParticipantRole, ConflictResponseType)
from .conflict_type import ConflictType
from .opposition_candidate import OppositionCandidate, OppositionSourceType


@dataclass(frozen=True)
class ConflictSnapshot:
    conflicts: tuple[ConflictState, ...] = ()
    transformed_count: int = 0
    opposition_candidates: tuple[OppositionCandidate, ...] = ()

    def __post_init__(self):
        conflicts, candidates = tuple(self.conflicts), tuple(self.opposition_candidates)
        if any(not isinstance(item, ConflictState) for item in conflicts):
            raise TypeError("conflicts must contain ConflictState values.")
        if any(not isinstance(item, OppositionCandidate) for item in candidates):
            raise TypeError("opposition_candidates must contain OppositionCandidate values.")
        object.__setattr__(self, "conflicts", conflicts)
        object.__setattr__(self, "opposition_candidates", candidates)
        if isinstance(self.transformed_count, bool) or not isinstance(self.transformed_count, int) or self.transformed_count < 0:
            raise ValueError("transformed_count must be non-negative.")


class ConflictManager:
    """Track conflict evolution and conditional obstacle candidates, without publishing events."""
    def __init__(self, snapshot=None, detector=None, *, world_memory=None):
        snapshot = snapshot or ConflictSnapshot()
        if not isinstance(snapshot, ConflictSnapshot):
            raise TypeError("snapshot must be ConflictSnapshot.")
        self._states = {item.id: item for item in snapshot.conflicts}
        self.transformed_count = snapshot.transformed_count
        self._opposition_candidates = list(snapshot.opposition_candidates)
        self.detector = detector or ConflictDetector()
        self.world_memory = world_memory

    @property
    def conflicts(self):
        return tuple(self._states[key] for key in sorted(self._states))

    @property
    def active_conflicts(self):
        active = {ConflictStatus.EMERGING, ConflictStatus.ACTIVE, ConflictStatus.ESCALATING,
                  ConflictStatus.STABLE, ConflictStatus.ESCALATED}
        return tuple(item for item in self.conflicts if item.status in active)

    @property
    def opposition_candidates(self):
        return tuple(self._opposition_candidates)

    def goal_pressures(self, lifecycle_manager):
        return tuple(getattr(lifecycle_manager, "pressures", ())) if lifecycle_manager is not None else ()

    def refresh(self, *, goals=(), motivations=(), resources=(), knowledge_by_character=None,
                cognition_by_character=None, goal_pressures=(), relationships=(), current_time=None):
        before_states = dict(self._states)
        goals = tuple(goals)
        detected = list(self.detector.detect(goals, motivations, resources))
        # Compare only caller-supplied character-scoped knowledge; conflict text stays generic.
        views = knowledge_by_character or {}
        owners = sorted(views)
        for index, left_id in enumerate(owners):
            left = _topics(views[left_id])
            for right_id in owners[index + 1:]:
                right = _topics(views[right_id])
                if left and right and left != right and left.intersection(right):
                    detected.append(_Detected(f"information:{left_id}:{right_id}", ConflictType.INFORMATION_CONFLICT,
                        (left_id, right_id), (), (), .35, "相关信息掌握程度不同，可能造成误解。"))
        cognition = cognition_by_character or {}
        cognitive_ids = sorted(cognition)
        for index, left_id in enumerate(cognitive_ids):
            left_beliefs = _beliefs(cognition[left_id])
            for right_id in cognitive_ids[index + 1:]:
                right_beliefs = _beliefs(cognition[right_id])
                shared = set(left_beliefs).intersection(right_beliefs)
                if any(left_beliefs[key] != right_beliefs[key] for key in shared):
                    detected.append(_Detected(f"value:{left_id}:{right_id}", ConflictType.VALUE_CONFLICT,
                        (left_id, right_id), (), (), .3, "角色对共同经历形成了不同解释。"))
        for pressure in goal_pressures:
            detected.append(_Detected(f"goal-pressure:{pressure.goal_id}", ConflictType.GOAL_CONFLICT,
                (_owner(goals, pressure.goal_id),), (pressure.goal_id,), (), pressure.severity,
                "当前目标推进受阻。"))
        for relationship in relationships:
            source = getattr(relationship, "source_id", None)
            target = getattr(relationship, "target_id", None)
            if not source or not target:
                continue
            trust = _relationship_value(relationship, "trust")
            hostility = _relationship_value(relationship, "hostility")
            severity = max(hostility, 1.0 - trust)
            if severity >= .65:
                detected.append(_Detected(
                    f"relationship:{source}:{target}", ConflictType.RELATIONSHIP_CONFLICT,
                    (source, target), (), (), min(1.0, severity),
                    "双方关系中的信任或敌意可能影响后续互动。",
                ))

        now = _time_text(current_time)
        current_ids = set()
        for item in detected:
            key = item.conflict_id
            current_ids.add(key)
            old = self._states.get(key)
            if old is not None and old.status in {
                ConflictStatus.RESOLVED, ConflictStatus.TRANSFORMED, ConflictStatus.ACCEPTED,
            }:
                continue
            kind = item.conflict_type
            if isinstance(kind, str):
                if kind == "internal_conflict":
                    continue
                kind = _type_from_string(kind)
            sources = tuple(getattr(item, "sources", ()))
            known_goal_ids = {goal.goal_id for goal in goals}
            if kind == ConflictType.INFORMATION_CONFLICT and len(sources) >= 2 and all(
                source in known_goal_ids for source in sources
            ):
                kind = ConflictType.GOAL_CONFLICT
            participants = tuple(value for value in item.participants if value)
            related_resources = sources if kind == ConflictType.RESOURCE_CONFLICT else tuple(
                getattr(item, "related_resources", ()))
            related_goals = (sources if kind == ConflictType.GOAL_CONFLICT and sources else
                             tuple(getattr(item, "related_goals", ())))
            baseline = min(1.0, max(getattr(item, "pressure", 0), getattr(item, "severity", 0)))
            severity = baseline if old is None or old.baseline_severity is None else min(
                1.0, max(0.0, old.severity + baseline - old.baseline_severity))
            status = _refreshed_status(old, severity, now) if old else ConflictStatus.EMERGING
            details = _participant_details(key, participants, goals, item)
            self._states[key] = ConflictState(
                key, kind, participants, related_goals, related_resources, severity, status,
                old.created_time if old else now, getattr(item, "description", ""),
                old.response_actions if old else (), details, now, old.evolution_count if old else 0,
                baseline, cause=getattr(item, "description", ""),
                created_from=("goal_pressure" if key.startswith("goal-pressure:") else
                              "relationship_state" if key.startswith("relationship:") else "world_analysis"),
            )
        live = {ConflictStatus.EMERGING, ConflictStatus.ACTIVE, ConflictStatus.ESCALATING,
                ConflictStatus.STABLE, ConflictStatus.ESCALATED}
        for key, old in tuple(self._states.items()):
            if (key.startswith("goal-pressure:") or key.startswith("relationship:")) \
                    and key not in current_ids and old.status in live:
                self._states[key] = replace(old, status=ConflictStatus.RESOLVED, severity=0.0,
                                            intensity=0.0, pressure=0.0,
                                            updated_time=now,
                                            resolved_by="goal_progress" if key.startswith("goal-pressure:")
                                            else "relationship_state")
        self._record_changes(before_states, timestamp=now, cause="conflict analysis refreshed")
        return self.conflicts

    def add(self, conflict: ConflictState):
        """Register a conflict state; adding it does not publish a world event."""
        if not isinstance(conflict, ConflictState):
            raise TypeError("conflict must be a ConflictState.")
        existing = self._states.get(conflict.id)
        if existing is not None and existing != conflict:
            raise ValueError(f"conflict id already exists: {conflict.id}")
        self._states[conflict.id] = conflict
        if existing is None:
            self._record_conflict_change(None, conflict, cause=conflict.cause or "conflict created")
        return conflict

    def resolve(self, conflict_id, *, outcome="resolved", resolved_by=None):
        old = self._require(conflict_id)
        if outcome == "transformed":
            self.transformed_count += 1
            status = ConflictStatus.TRANSFORMED
        elif outcome == "accepted":
            status = ConflictStatus.ACCEPTED
        elif outcome == "resolved":
            status = ConflictStatus.RESOLVED
        else:
            raise ValueError("outcome must be resolved, transformed, or accepted.")
        self._states[conflict_id] = replace(old, status=status, resolved_by=resolved_by)
        self._record_conflict_change(old, self._states[conflict_id], cause=resolved_by or outcome)
        return self._states[conflict_id]

    def escalate(self, conflict_id, severity=None):
        old = self._require(conflict_id)
        level = min(1.0, max(old.severity, old.severity + .1 if severity is None else float(severity)))
        self._states[conflict_id] = replace(old, status=ConflictStatus.ESCALATING, severity=level,
                                            intensity=level, pressure=level)
        self._record_conflict_change(old, self._states[conflict_id], cause="conflict intensity increased")
        return self._states[conflict_id]

    def record_response(self, conflict_id, action_type):
        old = self._require(conflict_id)
        actions = old.response_actions + (str(action_type),)
        self._states[conflict_id] = replace(old, response_actions=actions)
        self._record_conflict_change(old, self._states[conflict_id], cause=f"response:{action_type}")
        return self._states[conflict_id]

    def evolve(self, conflict_id, *, current_time=None, relationships=(), emotions=None,
               goal_importance=0.0, previous_actions=(), path_sufficient=True):
        """Move lifecycle and severity from observable signals; no action is selected here."""
        old = self._require(conflict_id)
        live = {ConflictStatus.EMERGING, ConflictStatus.ACTIVE, ConflictStatus.ESCALATING,
                ConflictStatus.STABLE, ConflictStatus.ESCALATED}
        if old.status not in live:
            return old
        labels = {str(value).casefold() for value in previous_actions}
        severity = old.severity
        if labels.intersection({"escalate", "compete", "threaten", "oppose"}):
            severity += .08
        if labels.intersection({"negotiate", "cooperate", "clarify", "share_information"}):
            severity -= .08
        relationships = tuple(item for item in relationships if
            getattr(item, "source_id", None) in old.participants and
            getattr(item, "target_id", None) in old.participants)
        if relationships:
            trust = sum(_relationship_value(item, "trust") for item in relationships) / len(relationships)
            hostility = sum(_relationship_value(item, "hostility") for item in relationships) / len(relationships)
            severity += .05 if hostility > .7 else -.04 if trust > .7 else 0.0
        emotions = emotions or {}
        if hasattr(emotions, "get"):
            values = [emotions.get(item) for item in old.participants if emotions.get(item) is not None]
            if any(getattr(item, "stress", 0) >= .8 for item in values):
                severity += .03
            if any(getattr(item, "anger", 0) >= .8 for item in values):
                severity += .04
        if not isinstance(goal_importance, bool) and isinstance(goal_importance, (int, float)):
            if goal_importance >= .8 and not path_sufficient:
                severity += .03
        severity = min(1.0, max(0.0, severity))
        now = _time_text(current_time)
        change = severity - old.severity
        if change >= .06:
            status = ConflictStatus.ESCALATING
        elif change <= -.06:
            # Falling pressure is evidence of mitigation, not proof that the
            # underlying disagreement has ended. Resolution remains explicit.
            status = ConflictStatus.ACTIVE
        elif _age_days(old.created_time, now) >= 14:
            status = ConflictStatus.STABLE
        elif old.status == ConflictStatus.EMERGING:
            status = ConflictStatus.ACTIVE
        else:
            status = old.status
        state = replace(old, severity=severity, intensity=severity, pressure=severity, status=status,
                        updated_time=now or old.updated_time,
                        evolution_count=old.evolution_count + 1)
        self._states[conflict_id] = state
        self._record_conflict_change(old, state, timestamp=now, cause="conflict evolved from observed signals")
        return state

    def generate_opposition_candidates(self, *, current_time, goal_priorities,
                                       path_sufficient, world_allows):
        """Return conditional opposition ideas only; never instantiate their sources."""
        candidates = []
        now = _time_text(current_time)
        for conflict in self.active_conflicts:
            if _age_days(conflict.created_time, now) < 7:
                continue
            if not any(float(goal_priorities.get(goal_id, 0.0)) >= .7
                       for goal_id in conflict.related_goals):
                continue
            if path_sufficient.get(conflict.id, True) or not world_allows.get(conflict.id, False):
                continue
            source_type, motivation, goal = {
                ConflictType.INFORMATION_CONFLICT: (OppositionSourceType.PERSON,
                    "依据自身目标谨慎决定是否分享信息", "在自身知识与限制范围内决定信息披露方式"),
                ConflictType.RESOURCE_CONFLICT: (OppositionSourceType.ENVIRONMENT,
                    "有限条件下维持现有资源供给", "在可用资源和环境条件下满足需求"),
                ConflictType.VALUE_CONFLICT: (OppositionSourceType.ORGANIZATION,
                    "维护其职责与公开规则", "按自身规则处理相互冲突的诉求"),
                ConflictType.GOAL_CONFLICT: (OppositionSourceType.PERSON,
                    "坚持自身目标并遵守个人限制", "在不放弃自身目标的前提下回应冲突"),
            }[conflict.conflict_type]
            candidates.append(OppositionCandidate(
                source_type, motivation, goal, conflict.related_resources,
                ("拥有自身目标与行动限制", "不得直接决定冲突结果"),
                f"可能影响冲突 {conflict.id} 的目标路径", conflict.id,
            ))
        self._opposition_candidates = candidates
        return tuple(candidates)

    def record_event(self, event):
        """Record an observed response and update only the linked conflict snapshot."""
        payload = getattr(event, "payload", {}) or {}
        params = payload.get("parameters", {}) if hasattr(payload, "get") else {}
        params = params if hasattr(params, "get") else {}
        conflict_ids = params.get("conflict_response", ())
        if isinstance(conflict_ids, str):
            conflict_ids = (conflict_ids,)
        action_type = payload.get("action_type", "action") if hasattr(payload, "get") else "action"
        event_type = str(getattr(event, "event_type", "")).casefold()
        strategy = params.get("conflict_response_type")
        effect = params.get("goal_effect", {})
        effect = effect if hasattr(effect, "get") else {}
        progress_delta = effect.get("progress_delta", 0)
        progressed = (effect.get("result") in {"progress", "effective", "success"}
                      or (isinstance(progress_delta, (int, float)) and not isinstance(progress_delta, bool)
                          and progress_delta > 0))
        explicit_id = params.get("conflict_id") or (payload.get("conflict_id") if hasattr(payload, "get") else None)
        if isinstance(explicit_id, str) and explicit_id:
            conflict_ids = (*tuple(conflict_ids), explicit_id)
        if event_type in {"conflict_misunderstanding", "information_misunderstood", "conflict_escalated"}:
            strategy = ConflictResponseType.ESCALATE.value
        elif event_type in {"conflict_communication", "information_shared", "conflict_clarified"}:
            strategy = ConflictResponseType.NEGOTIATE.value
        for conflict_id in dict.fromkeys(tuple(conflict_ids)):
            if conflict_id not in self._states:
                continue
            self.record_response(conflict_id, str(action_type))
            if strategy in {item.value for item in ConflictResponseType}:
                if strategy == ConflictResponseType.TRANSFORM.value:
                    self.resolve(conflict_id, outcome="transformed", resolved_by=getattr(event, "event_id", None))
                elif strategy == ConflictResponseType.ESCALATE.value:
                    self.escalate(conflict_id)
                elif event_type in {"conflict_communication", "information_shared", "conflict_clarified"}:
                    self.evolve(conflict_id, current_time=getattr(event, "timestamp", None),
                                previous_actions=("clarify", "share_information"))
                else:
                    self.evolve(conflict_id, current_time=getattr(event, "timestamp", None),
                                previous_actions=(strategy,))
            if progressed and conflict_id.startswith("goal-pressure:"):
                self.resolve(conflict_id)
        return tuple(self._states[key] for key in dict.fromkeys(tuple(conflict_ids)) if key in self._states)

    def pressure(self):
        return min(1.0, sum(item.pressure for item in self.active_conflicts) / 3.0)

    def snapshot(self):
        return ConflictSnapshot(self.conflicts, self.transformed_count, tuple(self._opposition_candidates))

    def _require(self, conflict_id):
        try:
            return self._states[conflict_id]
        except KeyError:
            raise KeyError(conflict_id) from None

    def _record_changes(self, before_states, *, timestamp=None, cause=""):
        if self.world_memory is None:
            return
        for key in sorted(set(before_states) | set(self._states)):
            before = before_states.get(key)
            after = self._states.get(key)
            if before != after:
                self._record_conflict_change(before, after, timestamp=timestamp, cause=cause)

    def _record_conflict_change(self, before, after, *, timestamp=None, cause=""):
        if self.world_memory is None or before == after:
            return
        state = after or before
        self.world_memory.record_conflict(
            state.id, "created" if before is None else "changed",
            before=_conflict_summary(before), after=_conflict_summary(after),
            timestamp=timestamp or getattr(state, "updated_time", None) or getattr(state, "created_time", None),
            cause=cause or "conflict state changed",
            metadata={"status": getattr(getattr(state, "status", None), "value", None),
                      "participants": tuple(state.participants),
                      "before": _conflict_summary(before), "after": _conflict_summary(after)},
        )


@dataclass(frozen=True)
class _Detected:
    conflict_id: str
    conflict_type: ConflictType
    participants: tuple[str, ...]
    related_goals: tuple[str, ...]
    related_resources: tuple[str, ...]
    severity: float
    description: str


def _participant_details(conflict_id, participants, goals, detected):
    sources = set(getattr(detected, "sources", ())) | set(getattr(detected, "related_goals", ()))
    goal_by_id = {goal.goal_id: goal for goal in goals}
    participant_goals = {
        owner_id: tuple(goal_by_id[source] for source in sources
                        if source in goal_by_id and goal_by_id[source].owner_id == owner_id)
        for owner_id in participants
    }
    result = []
    for index, character_id in enumerate(participants):
        if sources and len(participants) > 1:
            role = ConflictParticipantRole.INITIATOR if index == 0 else ConflictParticipantRole.OPPOSER
        else:
            role = ConflictParticipantRole.AFFECTED
        own_goals = participant_goals.get(character_id, ())
        motivation = ("推进自身目标：" + "；".join(goal.description for goal in own_goals)
                      if own_goals else "依据自身掌握的信息和处境作出判断")
        result.append(ConflictParticipant(character_id, conflict_id, role, motivation))
    return tuple(result)


def _refreshed_status(old, severity, now):
    if old.status in {ConflictStatus.RESOLVED, ConflictStatus.TRANSFORMED, ConflictStatus.ACCEPTED}:
        return old.status
    if severity >= old.severity + .08:
        return ConflictStatus.ESCALATING
    if old.status == ConflictStatus.EMERGING:
        return ConflictStatus.ACTIVE
    if old.status == ConflictStatus.ESCALATING and _age_days(old.created_time, now) < 14:
        return ConflictStatus.ESCALATING
    return ConflictStatus.STABLE if _age_days(old.created_time, now) >= 14 else ConflictStatus.ACTIVE


def _conflict_summary(state):
    if state is None:
        return None
    return {
        "status": getattr(getattr(state, "status", None), "value", state.status),
        "intensity": getattr(state, "intensity", getattr(state, "severity", 0.0)),
        "pressure": getattr(state, "pressure", 0.0),
        "resolved_by": getattr(state, "resolved_by", None),
    }


def _age_days(start, end):
    try:
        first = datetime.fromisoformat(start.replace("Z", "+00:00"))
        last = datetime.fromisoformat(end.replace("Z", "+00:00"))
        if first.tzinfo is None: first = first.replace(tzinfo=timezone.utc)
        if last.tzinfo is None: last = last.replace(tzinfo=timezone.utc)
        return max(0.0, (last - first).total_seconds() / 86400)
    except (AttributeError, TypeError, ValueError):
        return 0.0


def _relationship_value(relationship, name):
    value = getattr(relationship, name, 0.0)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if -100 <= value <= 100 and (value < 0 or value > 1):
            return (value + 100) / 200
        return max(0.0, min(1.0, float(value)))
    return 0.0


def _type_from_string(value):
    try:
        return ConflictType(value)
    except ValueError:
        return ConflictType.GOAL_CONFLICT


def _topics(records):
    values = set()
    for record in records:
        for value in (getattr(record, "fact_id", None), getattr(record, "known_content", None)):
            if isinstance(value, str) and value.strip():
                text = value.casefold()
                for tag in ("异常", "调查", "能源", "医院", "地下室", "真相", "线索", "传闻", "rumor", "anomaly", "energy"):
                    if tag in text:
                        values.add(tag)
    return values


def _beliefs(value):
    items = value.get("beliefs", ()) if hasattr(value, "get") else getattr(value, "beliefs", ())
    return {getattr(item, "source_fact", ""): getattr(item, "interpretation", "") for item in items
            if getattr(item, "source_fact", "") and getattr(item, "interpretation", "")}


def _owner(goals, goal_id):
    return next((item.owner_id for item in goals if item.goal_id == goal_id), "unknown")


def _time_text(value):
    if value is None:
        return ""
    return value.isoformat() if hasattr(value, "isoformat") else str(value)
