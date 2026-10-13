from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.narrative.opportunity import NarrativeOpportunity, OpportunitySourceType


def test_opportunity_is_immutable_and_describes_a_possibility_not_a_world_event():
    opportunity = NarrativeOpportunity(
        "op-1", OpportunitySourceType.GOAL, related_goal="investigate",
        visibility="owner", importance=.7, possible_actions=["ask", "ignore"],
        description="或许可以寻找新的信息来源。",
    )
    assert opportunity.possible_actions == ("ask", "ignore")
    with pytest.raises(FrozenInstanceError):
        opportunity.importance = .1
    assert not hasattr(opportunity, "event_type")
