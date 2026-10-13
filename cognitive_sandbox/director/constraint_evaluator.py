from __future__ import annotations

from dataclasses import replace
from collections.abc import Mapping

from cognitive_sandbox.narrative.narrative_anchor import NarrativeAnchorValidator, NarrativeConstraint

from .director_constraint import DirectorConstraint, DirectorConstraintStatus
from .constraint_type import ConstraintType
from .constraint_explanation import ConstraintExplanation


class DirectorConstraintEvaluator:
    """Validate a soft direction against public presence and causal-travel rules."""

    def __init__(self, anchor_validator=None):
        self.anchor_validator = anchor_validator or NarrativeAnchorValidator()

    def to_narrative_constraints(self, constraint: DirectorConstraint):
        targets = tuple(item for item in (constraint.target or "world").split(",") if item) or ("world",)
        priority = round(constraint.priority * 10)
        conditions = tuple(dict.fromkeys((*constraint.conditions, "respect_world_rules", "no_teleportation")))
        return tuple(NarrativeConstraint(target, constraint.intent.description, priority, conditions)
                     for target in targets)

    def evaluate_candidate(self, candidate, constraints=()):
        """Return (allowed, score_delta, explanations) using candidate-visible text only."""
        text = _candidate_text(candidate)
        delta = 0.0
        explanations = []
        allowed = True
        for constraint in constraints:
            if not isinstance(constraint, DirectorConstraint) or not _matches(constraint, text):
                continue
            kind = constraint.constraint_type
            if kind is ConstraintType.FORBID:
                allowed = False
                effect = "blocked"
                reason = f"候选与禁止约束“{constraint.intent.description}”冲突。"
            elif kind is ConstraintType.AVOID:
                delta -= constraint.strength.weight * constraint.priority
                effect = "score_reduced"
                reason = f"候选与避免方向“{constraint.intent.description}”相符，降低其优先级。"
            else:
                delta += constraint.strength.weight * constraint.priority
                effect = "score_increased"
                reason = f"候选符合偏好“{constraint.intent.description}”，提高其优先级。"
            explanations.append(ConstraintExplanation(constraint.id, effect, reason, (_candidate_id(candidate),)))
        return allowed, delta, tuple(explanations)

    def score_path(self, path_text, constraints=(), *, candidate_id="path"):
        class CandidateView:
            pass
        candidate = CandidateView()
        candidate.description = path_text
        candidate.title = path_text
        candidate.candidate_id = candidate_id
        return self.evaluate_candidate(candidate, constraints)

    def evaluate(self, constraint, *, presences=(), current_location=None, reachable_locations=()):
        if not isinstance(constraint, DirectorConstraint):
            raise TypeError("constraint must be DirectorConstraint.")
        anchors = self.to_narrative_constraints(constraint)
        validations = tuple(self.anchor_validator.validate(
            anchor, presences, current_location=current_location, reachable_locations=reachable_locations
        ) for anchor in anchors)
        rejected = next((item for item in validations if not item.accepted), None)
        if rejected is not None:
            return replace(constraint, status=DirectorConstraintStatus.BLOCKED), rejected.reason
        reasons = tuple(dict.fromkeys(item.reason for item in validations))
        return replace(constraint, status=DirectorConstraintStatus.SEARCHING), ";".join(reasons)


def _candidate_id(candidate):
    return str(getattr(candidate, "candidate_id", getattr(candidate, "title", "candidate")))


def _candidate_text(candidate):
    if isinstance(candidate, Mapping):
        values = [value for value in candidate.values() if isinstance(value, str)]
        values.extend(str(value) for value in candidate.get("conditions", ()))
        return " ".join(values).casefold()
    values = []
    for name in ("event_type", "title", "description", "rationale", "category", "target", "intent"):
        value = getattr(candidate, name, None)
        if isinstance(value, str):
            values.append(value)
    values.extend(str(value) for value in getattr(candidate, "conditions", ()))
    return " ".join(values).casefold()


def _matches(constraint, text):
    category = constraint.category.casefold()
    terms = {
        "truth_reveal": ("truth", "reveal", "secret", "真相", "揭露", "揭开", "知道", "发现异常核心"),
        "death": ("death", "die", "fatal", "死亡", "死去", "丧命"),
        "romance": ("romance", "love", "恋爱", "浪漫", "情侣"),
        "cooperation": ("cooperat", "partner", "shared goal", "共同目标", "合作", "伙伴", "协作", "关系"),
        "investigation": ("investigat", "clue", "调查", "线索"),
    }.get(category, tuple(word for word in constraint.intent.description.casefold().split() if len(word) > 1))
    return any(term.casefold() in text for term in terms)
