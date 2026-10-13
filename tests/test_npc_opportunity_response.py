from types import SimpleNamespace

from cognitive_sandbox.agency.agency_evaluator import AgencyEvaluator, AgencyTendency
from cognitive_sandbox.agency.agency_state import AgencyStateManager
from cognitive_sandbox.narrative.opportunity import NarrativeOpportunity
from cognitive_sandbox.npc.autonomous.npc_scheduler import NpcScheduler


class _OpportunityService:
    def for_character(self, owner_id):
        return (NarrativeOpportunity(
            "op-npc", "GOAL", related_goal="npc-a:investigate", related_character=owner_id,
            visibility="owner", visible_character_ids=(owner_id,), importance=.8, urgency=.5,
            description="可以尝试核实自己已知的线索。",
        ),)


def test_npc_opportunity_becomes_an_agency_candidate_without_direct_execution():
    manager = AgencyStateManager(character_ids=("npc-a",))
    scheduler = NpcScheduler(agency_manager=manager, agency_evaluator=AgencyEvaluator())
    scheduler.opportunity_service = _OpportunityService()
    candidates = scheduler._opportunity_candidates(
        "npc-a", (), SimpleNamespace(relationship_manager=None, narrative_pressure=None),
        None, {}, None, None, AgencyTendency(.8, True, "主动倾向较高"),
    )
    assert candidates
    assert candidates[0].action.actor_id == "npc-a"
    assert candidates[0].action.action_type == "investigate"
    assert manager.snapshot().autonomous_action_history == ()
