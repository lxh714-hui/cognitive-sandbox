from cognitive_sandbox.application.action_intent_parser import ActionIntentParser
from cognitive_sandbox.application.action_semantic_mapper import ActionSemanticMapper
from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.action_intent import ActionIntent
from cognitive_sandbox.narrative.opportunity import NarrativeOpportunity, OpportunitySourceType


def test_same_goal_different_phrasing_targets_and_reuses_opportunity_branch():
    parser = ActionIntentParser()
    mapper = ActionSemanticMapper()
    action = parser.parse("player", "看看钟")
    assert action.intent == "inspect"
    assert action.object == "钟"
    opportunity_action = ActionCandidate(
        "inspect", actor_id="player", intent="inspect", target="钟",
        metadata={"objective": "inspect:钟", "method": "inspect", "risk": .25,
                   "relationship_effect": "no_direct_change", "expected_effect": "inspect_target"},
    )
    opportunity = NarrativeOpportunity(
        "investigate_clock", OpportunitySourceType.WORLD, description="钟停在12:03。",
        visibility="public", candidate_actions=(opportunity_action,),
    )
    mapping = mapper.map_to_existing(action, (opportunity_action,), (opportunity,))
    assert mapping.target_opportunity == "investigate_clock"
    assert mapping.reused_existing_branch
    assert mapping.classification == "reuse_existing"


def test_high_risk_stealth_method_does_not_merge_with_open_inspection():
    parser = ActionIntentParser()
    mapper = ActionSemanticMapper()
    opportunity_action = mapper.candidate_for(parser.parse("player", "查看钟"))
    stealth = ActionIntent(
        "player", "偷偷观察钟", "inspect", object="钟",
        parameters={"method": "stealth", "risk": .9},
    )
    opportunity = NarrativeOpportunity(
        "clock", OpportunitySourceType.WORLD, description="钟停在12:03。",
        visibility="public", candidate_actions=(opportunity_action,),
    )
    mapping = mapper.map_to_existing(stealth, (), (opportunity,))
    assert mapping.target_opportunity is None
    assert mapping.classification == "new_branch"


def test_branch_similarity_returns_score_without_merging_nodes():
    from cognitive_sandbox.application.branch_similarity_evaluator import (
        BasicBranchSimilarityEvaluator, BranchSemantics,
    )
    evaluator = BasicBranchSimilarityEvaluator()
    left = BranchSemantics("investigate clock", "look", .2, "neutral", "learn time")
    right = BranchSemantics("investigate clock", "look", .2, "neutral", "learn time")
    assert evaluator.evaluate(left, right) == 1.0
