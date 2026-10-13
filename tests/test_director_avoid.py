from cognitive_sandbox.director.constraint_type import ConstraintType
from cognitive_sandbox.director.director_intent import DirectorIntent, DirectorIntentType
from cognitive_sandbox.director.director_constraint import DirectorConstraint
from cognitive_sandbox.director.constraint_evaluator import DirectorConstraintEvaluator


def test_avoid_reduces_matching_candidate_score_without_removing_it():
    intent = DirectorIntent(DirectorIntentType.RELATIONSHIP_DEVELOPMENT, "liangjing,liuyiyi",
                            "避免过早恋爱线", constraint_type=ConstraintType.AVOID,
                            category="romance")
    constraint = DirectorConstraint("avoid1", intent, intent.target, .8)
    candidate = {"event_type": "romance_develops", "description": "两人关系进入恋爱"}
    allowed, delta, explanations = DirectorConstraintEvaluator().evaluate_candidate(candidate, (constraint,))
    assert allowed and delta < 0
    assert explanations[0].effect == "score_reduced"
