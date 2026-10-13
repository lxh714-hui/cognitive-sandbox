from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from collections.abc import Mapping


@dataclass(frozen=True)
class AgencyTendency:
    score: float
    should_act: bool
    reason: str

    def __post_init__(self):
        if isinstance(self.score, bool) or not isinstance(self.score, (int, float)) or not 0 <= self.score <= 1:
            raise ValueError("score must be between 0 and 1.")
        if not isinstance(self.should_act, bool) or not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("tendency requires a boolean decision and reason.")
        object.__setattr__(self, "score", float(self.score))


class AgencyEvaluator:
    """Deterministic initiative threshold using goal, affect, elapsed time and environment."""

    def evaluate(self, agency, *, goal=None, emotion=None, current_time=None,
                 recent_actions=(), environment=None, motivation=None, cognition=None,
                 current_pressure=None, information_need=0.0):
        if goal is None:
            goal_strength = .15
        else:
            goal_strength = float(getattr(goal, "priority", .5)) * (1 - float(getattr(goal, "progress", 0)))
        curiosity = _get(emotion, "curiosity", .5)
        stress = _get(emotion, "stress", 0.0)
        initiative = float(getattr(agency, "initiative", .5))
        motive = float(getattr(agency, "motivation_strength", .5))
        focus = float(getattr(agency, "goal_focus", .5))
        public_goal = getattr(motivation, "public_goal", "") if motivation is not None else ""
        cognitive_style = cognition.get("cognitive_style") if isinstance(cognition, Mapping) else None
        cognitive_drive = .04 * _get(cognitive_style, "suspicious", .5) + .02 * _get(cognitive_style, "strategic", .5)
        motive_signal = .03 if isinstance(public_goal, str) and public_goal.strip() else 0.0
        env = environment or {}
        clue = .16 if env.get("relevant_clue") else 0.0
        pressure = _pressure(current_pressure)
        score = (.25 * initiative + .22 * motive + .23 * focus + .18 * goal_strength
                 + .12 * curiosity + clue + cognitive_drive + motive_signal
                 + .08 * pressure + .08 * _bounded(information_need))
        score -= .08 * stress
        score -= .06 * float(getattr(agency, "action_frequency", 0.0))
        now_text = current_time.isoformat() if hasattr(current_time, "isoformat") else current_time
        last = getattr(agency, "last_action_time", None)
        if last and now_text:
            try:
                then = datetime.fromisoformat(last.replace("Z", "+00:00"))
                now = datetime.fromisoformat(now_text.replace("Z", "+00:00"))
                if then.tzinfo is None:
                    then = then.replace(tzinfo=timezone.utc)
                if now.tzinfo is None:
                    now = now.replace(tzinfo=timezone.utc)
                hours = max(0, (now - then).total_seconds() / 3600)
                # Small simulation ticks can be minutes apart; avoid suppressing
                # an explicitly eligible goal action when its world tick advances
                # by ten minutes. The action-frequency term remains the soft cap.
                if hours < .05:
                    score *= .2
                elif hours >= 72:
                    score += min(.12, (hours - 72) / 24 * .02)
            except (TypeError, ValueError):
                pass
        if now_text:
            try:
                now_value = datetime.fromisoformat(now_text.replace("Z", "+00:00"))
                if now_value.tzinfo is None:
                    now_value = now_value.replace(tzinfo=timezone.utc)
                recent_count = 0
                for entry in tuple(recent_actions):
                    if len(entry) != 3:
                        continue
                    then = datetime.fromisoformat(entry[2].replace("Z", "+00:00"))
                    if then.tzinfo is None:
                        then = then.replace(tzinfo=timezone.utc)
                    age = (now_value - then).total_seconds() / 3600
                    if 0 <= age < 24:
                        recent_count += 1
                score -= min(.12, .04 * recent_count)
            except (TypeError, ValueError, AttributeError):
                pass
        score = min(1.0, max(0.0, score))
        reason = "目标和当前可见线索支持主动行动" if score >= .45 else "当前主动倾向较低，保留观察或日常行为"
        return AgencyTendency(score, score >= .45, reason)

    @staticmethod
    def score_action(base_score, *, action_type, recent_actions=(), feedback=(), current_time=None,
                     current_pressure=None, information_need=0.0, goal_stagnation=0.0,
                     conflicts=(), emotion=None, cognition=None, relationship=None, risk=0.0):
        """Rank a candidate using visible need, novelty, pressure and recorded outcomes."""
        score = float(base_score)
        action_type = str(action_type)
        recent_actions = _within_days(recent_actions, current_time, 7)
        feedback = _within_days(feedback, current_time, 7, time_index=2)
        recent_types = [entry[1] for entry in tuple(recent_actions) if len(entry) == 3]
        same_recent = recent_types[-5:].count(action_type)
        novelty = .08 if action_type not in recent_types[-3:] else 0.0
        score += novelty + .08 * _bounded(information_need) + .08 * _pressure(current_pressure)
        score -= min(.36, .13 * same_recent)
        recent_feedback = [entry for entry in tuple(feedback)
                           if len(entry) == 5 and entry[1] == action_type][-3:]
        ineffective = sum(1 for entry in recent_feedback if entry[4] < .35)
        score -= min(.3, .12 * ineffective)
        # Stagnation changes relative preference; it never creates or mandates an action.
        stagnation = _bounded(goal_stagnation)
        weak_types = {entry[1] for entry in tuple(feedback)
                      if len(entry) == 5 and entry[4] < .35}
        if action_type in weak_types:
            score -= .35 * stagnation
        if stagnation >= .35 and action_type in {"socialize", "travel", "observe", "ask", "inspect"}:
            score += .18 * stagnation
        score += AgencyEvaluator.conflict_response_score(
            action_type, conflicts=conflicts, emotion=emotion, cognition=cognition,
            relationship=relationship, risk=risk, goal_stagnation=stagnation,
        )
        return max(0.0, min(1.0, score))

    @staticmethod
    def conflict_response_score(action_type, *, conflicts=(), emotion=None, cognition=None,
                                relationship=None, risk=0.0, goal_stagnation=0.0):
        """Legacy additive modifier; does not choose or execute an action.

        Phase 16 Agency uses ``conflict_response_candidates`` as context for
        ranking. This method remains solely for older callers/tests.
        """
        from cognitive_sandbox.conflict.conflict_context import LegacyConflictAdapter
        return LegacyConflictAdapter.legacy_score_modifier(
            action_type, conflicts=tuple(conflicts), emotion=emotion,
            cognition=cognition, relationship=relationship, risk=risk,
            goal_stagnation=goal_stagnation,
        )

    @staticmethod
    def conflict_response_candidates(*, conflicts=(), emotion=None, cognition=None,
                                     relationship=None, risk=0.0, goal_stagnation=0.0):
        """Return candidate response propensities for the caller's Agency ranking."""
        from cognitive_sandbox.conflict.conflict_state import ConflictResponseCandidate, ConflictResponseType
        conflicts = tuple(conflicts)
        if not conflicts:
            return ()
        kind_types = {getattr(getattr(item, "conflict_type", None), "value", "") for item in conflicts}
        stress = _get(emotion, "stress", 0.0)
        fear = _get(emotion, "fear", 0.0)
        anger = _get(emotion, "anger", 0.0)
        calmness = _get(emotion, "calmness", .5)
        suspicion = _get(cognition.get("cognitive_style") if isinstance(cognition, Mapping) else None,
                         "suspicious", .5)
        analytical = _get(cognition.get("cognitive_style") if isinstance(cognition, Mapping) else None,
                          "analytical", .5)
        trust = _relationship_signal(relationship, "trust")
        affinity = _relationship_signal(relationship, "affinity")
        hostility = _relationship_signal(relationship, "hostility")
        risk = _bounded(risk)
        severity = max((_bounded(getattr(item, "severity", 0.0)) for item in conflicts), default=0.0)
        stagnation = _bounded(goal_stagnation)
        values = {
            "avoid": .15 + .28 * fear + .16 * stress + .12 * risk - .12 * trust,
            "negotiate": .18 + .20 * trust + .12 * analytical + .10 * calmness - .12 * hostility,
            "cooperate": .18 + .18 * trust + .14 * affinity + .10 * calmness - .08 * hostility,
            "compete": .12 + .20 * hostility + .12 * suspicion +
                       (.14 if "resource_conflict" in kind_types else 0.0),
            "escalate": .10 + .20 * anger + .18 * hostility + .12 * severity - .18 * risk,
            "transform": .12 + .24 * stagnation + .12 * fear + .10 * analytical,
        }
        return tuple(ConflictResponseCandidate(response, _bounded(score))
                     for response, score in ((item.value, values[item.value]) for item in ConflictResponseType))


def _get(source, name, default):
    value = getattr(source, name, None)
    if value is None and isinstance(source, Mapping):
        value = source.get(name)
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else default


def _bounded(value):
    return max(0.0, min(1.0, float(value))) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0


def _relationship_signal(source, name):
    value = _get(source, name, 0.0)
    if -100 <= value <= 100 and value < 0:
        return (value + 100) / 200
    if value > 1:
        return min(1.0, value / 100)
    return _bounded(value)


def _pressure(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _bounded(value)
    if value is not None:
        return sum(_get(value, field, 0.0) for field in ("urgency", "danger", "unresolved_degree")) / 3
    return 0.0


def _within_days(entries, current_time, days, *, time_index=2):
    try:
        now_text = current_time.isoformat() if hasattr(current_time, "isoformat") else current_time
        now = datetime.fromisoformat(now_text.replace("Z", "+00:00"))
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        result = []
        for entry in tuple(entries):
            if len(entry) <= time_index:
                continue
            then = datetime.fromisoformat(entry[time_index].replace("Z", "+00:00"))
            if then.tzinfo is None:
                then = then.replace(tzinfo=timezone.utc)
            age = (now - then).total_seconds()
            if 0 <= age <= days * 86400:
                result.append(entry)
        return tuple(result)
    except (AttributeError, TypeError, ValueError):
        return tuple(entries)
