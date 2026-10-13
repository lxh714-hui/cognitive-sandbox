from cognitive_sandbox.director.constraint_type import ConstraintType
from cognitive_sandbox.director.director_intent import DirectorIntent, DirectorIntentType
from cognitive_sandbox.director.director_constraint import DirectorConstraint
from cognitive_sandbox.director.constraint_evaluator import DirectorConstraintEvaluator


def test_forbid_blocks_matching_candidate_but_does_not_create_an_event():
    intent = DirectorIntent(DirectorIntentType.CUSTOM_DIRECTION, None, "禁止主角死亡",
                            constraint_type=ConstraintType.FORBID, category="death")
    constraint = DirectorConstraint("forbid1", intent, None, 1.0)
    allowed, delta, explanations = DirectorConstraintEvaluator().evaluate_candidate(
        {"event_type": "fatal_attack", "description": "主角可能死亡"}, (constraint,))
    assert not allowed and delta == 0
    assert explanations[0].effect == "blocked"
