from datetime import datetime
from types import SimpleNamespace

from cognitive_sandbox.application.world_tree_manager import WorldTreeManager
from cognitive_sandbox.narrative.opportunity import (
    NarrativeOpportunityService,
    OpportunityProposal,
    OpportunityProposalService,
    ProposalContext,
    ProposalType,
    ProposalValidator,
)
from cognitive_sandbox.npc.autonomous.npc_scheduler import NpcScheduler


class Provider:
    def __init__(self, values):
        self.values = tuple(values)
        self.context = None

    def propose(self, context):
        self.context = context
        return self.values


def make_context(**overrides):
    values = {
        "current_time": "2026-10-13T09:00:00",
        "location": "home",
        "world_state": {
            "world_id": "anchor", "name": "锚点", "location": "home",
            "public_locations": ["home", "store"], "secret_truth": "secret knowledge",
            "world_variables": {"hidden_fact": "classified"},
        },
        "character_states": [
            {"character_id": "liangjing", "name": "梁景", "location": "home",
             "public_goal": "重新开始生活", "hidden_goal": "secret knowledge"},
            {"character_id": "liuyiyi", "name": "柳依依", "location": "store",
             "public_goal": "寻找异常线索", "private_knowledge": "the secret truth"},
        ],
        "recent_events": [{"event_id": "e1", "event_type": "return_home", "timestamp": "Day 1",
                           "public_summary": "梁景回到住所", "metadata": {"secret": "hidden fact"},
                           "is_public": True}],
    }
    values.update(overrides)
    return ProposalContext.from_public_data(**values)


def test_proposal_creation_does_not_change_world_state():
    context = make_context()
    before = dict(context.public_world_state)
    proposal = OpportunityProposal("p1", "plot_development", "住所里或许还有值得检查的旧物。",
                                  related_entities=("location:home",), confidence=.8)
    provider = Provider((proposal,))
    service = OpportunityProposalService(provider)
    assert service.generate(context) == (proposal,)
    assert dict(context.public_world_state) == before
    assert service.pending == (proposal,)


def test_unapproved_proposal_does_not_create_event_or_opportunity():
    context = make_context()
    proposal = OpportunityProposal("p2", "plot_development", "住所里或许还有值得检查的旧物。",
                                  related_entities=("location:home",), confidence=.8)
    provider = Provider((proposal,))
    service = OpportunityProposalService(provider)
    service.generate(context)
    opportunity_service = SimpleNamespace(registered=[], register=lambda item: opportunity_service.registered.append(item))
    tree = WorldTreeManager("anchor")
    assert not opportunity_service.registered
    assert not tree.candidate_actions
    assert service.pending == (proposal,)


def test_hidden_information_is_filtered_before_provider_and_validator():
    context = make_context()
    provider = Provider(())
    OpportunityProposalService(provider).generate(context)
    visible_text = repr((dict(provider.context.public_world_state), provider.context.public_character_states,
                         provider.context.recent_events))
    assert "secret_truth" not in visible_text
    assert "hidden_fact" not in visible_text
    assert "private_knowledge" not in visible_text
    assert "hidden_goal" not in visible_text
    assert "metadata" not in visible_text

    leaking = OpportunityProposal("p3", "plot_development", "隐藏知识会证明秘密真相。", confidence=.9)
    result = ProposalValidator().validate(leaking, context)
    assert not result.valid
    assert any("hidden" in item for item in result.errors)


def test_valid_proposal_approval_creates_opportunity_and_world_tree_candidate():
    context = make_context()
    proposal = OpportunityProposal(
        "p4", ProposalType.PLOT_DEVELOPMENT, "住所里的墙钟或许值得重新检查。",
        related_entities=("location:home",), conditions={"location": "home"},
        confidence=.9, possible_actions=("查看墙钟",),
    )
    service = OpportunityProposalService(Provider((proposal,)))
    service.generate(context)
    opportunity_manager = NarrativeOpportunityService(world_clock=SimpleNamespace(current_time=lambda: datetime(2026, 10, 13, 9)))
    tree = WorldTreeManager("anchor")
    result = service.approve(proposal.proposal_id, context, opportunity_service=opportunity_manager,
                             world_tree_manager=tree)
    assert result.approved
    assert result.opportunity in opportunity_manager.manager.snapshot()
    assert result.opportunity.source == "ai_proposal"
    assert result.world_tree_branches
    assert tree.candidate_actions


def test_npc_proposal_enters_agency_candidates_without_execution():
    context = make_context()
    proposal = OpportunityProposal(
        "p5", "character_action", "柳依依或许会到便利店附近继续调查。",
        related_entities=("character:liuyiyi", "location:store"),
        possible_actions=("前往便利店调查",), confidence=.85, source_character_id="liuyiyi",
    )
    proposal_service = OpportunityProposalService(Provider((proposal,)))
    proposal_service.generate(context)
    opportunities = SimpleNamespace(registered=[], register=lambda item: opportunities.registered.append(item))
    approved = proposal_service.approve("p5", context, opportunity_service=opportunities).opportunity
    assert approved is not None

    class Agency:
        def snapshot(self):
            return SimpleNamespace(autonomous_action_history=(), action_feedback_history=())

    class Evaluator:
        def score_action(self, base, **kwargs):
            return base

    scheduler = NpcScheduler(agency_manager=Agency(), agency_evaluator=Evaluator())
    scheduler.opportunity_service = SimpleNamespace(for_character=lambda character_id: (approved,))
    candidates = scheduler._opportunity_candidates(
        "liuyiyi", (), SimpleNamespace(), datetime(2026, 10, 13, 9), {}, None, None,
        SimpleNamespace(should_act=False),
    )
    assert candidates
    assert candidates[0].action.actor_id == "liuyiyi"
    assert candidates[0].action.action_type == "investigate"
    assert candidates[0].score < .5  # the regular Agency score still affects selection
    assert not hasattr(candidates[0].action, "event")

