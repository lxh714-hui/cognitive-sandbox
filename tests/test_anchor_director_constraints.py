"""Small public-candidate checks using the same constraints used by Anchor's DirectorManager."""
from cognitive_sandbox.director.constraint_evaluator import DirectorConstraintEvaluator
from cognitive_sandbox.director.constraint_type import ConstraintType
from cognitive_sandbox.director.director_constraint import DirectorConstraint
from cognitive_sandbox.director.director_intent import DirectorIntent, DirectorIntentType


def _constraint(text, kind, category, target=None):
    intent = DirectorIntent(DirectorIntentType.CUSTOM_DIRECTION, target, text,
                            constraint_type=kind, category=category)
    return DirectorConstraint(f"anchor-{category}", intent, target, .8)


def test_anchor_avoid_early_truth_reveal_reduces_public_candidate_weight():
    constraint = _constraint("不要让梁景过早知道异常真相", ConstraintType.AVOID, "truth_reveal", "liangjing")
    allowed, delta, _ = DirectorConstraintEvaluator().evaluate_candidate(
        {"event_type": "truth_reveal", "description": "梁景发现异常真相"}, (constraint,))
    assert allowed and delta < 0


def test_anchor_cooperation_preference_increases_shared_event_weight():
    constraint = _constraint("希望梁景和柳依依成为合作伙伴", ConstraintType.PREFER, "cooperation",
                             "liangjing,liuyiyi")
    allowed, delta, _ = DirectorConstraintEvaluator().evaluate_candidate(
        {"event_type": "shared_goal_opportunity", "description": "共同目标促成合作"}, (constraint,))
    assert allowed and delta > 0


def test_anchor_no_death_forbid_excludes_matching_candidate_only():
    constraint = _constraint("禁止主角死亡", ConstraintType.FORBID, "death", "liangjing")
    evaluator = DirectorConstraintEvaluator()
    allowed, _, _ = evaluator.evaluate_candidate({"event_type": "fatal_attack"}, (constraint,))
    allowed_safe, _, _ = evaluator.evaluate_candidate({"event_type": "investigation_lead"}, (constraint,))
    assert not allowed and allowed_safe
