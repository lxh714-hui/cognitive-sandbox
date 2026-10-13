from cognitive_sandbox.application.action_intent_parser import ActionIntentParser
from cognitive_sandbox.application.action_semantic_mapper import ActionSemanticMapper
from cognitive_sandbox.domain.action_intent import ActionIntent


def test_equivalent_natural_language_actions_reuse_existing_candidate():
    parser = ActionIntentParser()
    mapper = ActionSemanticMapper()
    first = parser.parse("player", "问问老板有没有奇怪的人")
    variant = parser.parse("player", "去问问老板有没有奇怪的人")

    existing = mapper.candidate_for(first)
    mapping = mapper.map_to_existing(variant, (existing,))

    assert mapping.reused_existing_branch
    assert mapping.matched_candidate is existing


def test_stealth_method_and_risk_do_not_overfit_to_open_observation_candidate():
    parser = ActionIntentParser()
    mapper = ActionSemanticMapper()
    open_observation = parser.parse("player", "观察老板")
    stealth_observation = parser.parse("player", "偷偷观察老板")

    mapping = mapper.map_to_existing(stealth_observation, (mapper.candidate_for(open_observation),))

    assert stealth_observation.intent == "observe"
    assert stealth_observation.parameters["method"] == "stealth"
    assert stealth_observation.parameters["risk"] == .75
    assert not mapping.reused_existing_branch
    assert mapping.candidate is not mapping.matched_candidate


def test_semantic_mapping_requires_matching_goal_method_and_social_effect():
    mapper = ActionSemanticMapper()
    original = ActionIntent(
        "player", "问老板", "ask", "老板", parameters={"objective": "查明陌生人", "risk": .2}
    )
    different_goal = ActionIntent(
        "player", "问老板", "ask", "老板", parameters={"objective": "打听天气", "risk": .2}
    )
    different_relationship = ActionIntent(
        "player", "问老板", "ask", "老板",
        parameters={"objective": "查明陌生人", "risk": .2, "relationship_effect": "pressure"},
    )

    candidate = mapper.candidate_for(original)
    assert not mapper.map_to_existing(different_goal, (candidate,)).reused_existing_branch
    assert not mapper.map_to_existing(different_relationship, (candidate,)).reused_existing_branch
