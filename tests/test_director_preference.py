from cognitive_sandbox.director.constraint_type import ConstraintType
from cognitive_sandbox.director.director_intent import DirectorIntent, DirectorIntentType
from cognitive_sandbox.director.director_constraint import DirectorConstraint
from cognitive_sandbox.director.constraint_evaluator import DirectorConstraintEvaluator


def test_preference_increases_matching_cooperation_candidate_score():
    intent = DirectorIntent(DirectorIntentType.RELATIONSHIP_DEVELOPMENT, "liangjing,liuyiyi",
                            "希望梁景和柳依依成为合作伙伴", constraint_type=ConstraintType.PREFER,
                            category="cooperation")
    constraint = DirectorConstraint("prefer1", intent, intent.target, .8)
    allowed, delta, explanations = DirectorConstraintEvaluator().evaluate_candidate(
        {"event_type": "shared_goal_opportunity", "description": "共同目标促成合作伙伴关系"}, (constraint,))
    assert allowed and delta > 0
    assert explanations[0].effect == "score_increased"
