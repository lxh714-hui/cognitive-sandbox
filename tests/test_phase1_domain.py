from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.domain.cognition import CognitiveUpdateProposal, ProposalOperation
from cognitive_sandbox.domain.observations import ObservationRecord
from cognitive_sandbox.domain.world_events import WorldEvent


def test_world_event_creation_preserves_structured_fields():
    event = WorldEvent(
        event_id="event-001",
        branch_id="main",
        world_id="harbor",
        event_type="BREAK_OBJECT",
        actor_id="liang-jing",
        payload={"object_id": "cup_001"},
        world_revision=1,
    )

    assert event.event_id == "event-001"
    assert event.branch_id == "main"
    assert event.world_id == "harbor"
    assert event.event_type == "BREAK_OBJECT"
    assert event.actor_id == "liang-jing"
    assert event.payload["object_id"] == "cup_001"
    assert event.world_revision == 1


def test_observation_record_has_agent_and_source_refs():
    observation = ObservationRecord(
        observation_id="observation-001",
        agent_id="lin-xia",
        source_refs=["event-001"],
        observed_at="2026-10-11T10:00:00+00:00",
        channel="visual",
        content="梁景打碎了杯子",
        uncertainty=0.1,
    )

    assert observation.agent_id == "lin-xia"
    assert observation.source_refs == ("event-001",)
    assert observation.content == "梁景打碎了杯子"


def test_cognitive_update_proposal_creation():
    proposal = CognitiveUpdateProposal(
        proposal_id="proposal-001",
        agent_id="lin-xia",
        target_layer="working_memory",
        operation="activate",
        source_refs=("observation-001",),
        reason="The observation is relevant to the current situation.",
        base_cognitive_revision=0,
        world_revision=1,
    )

    assert proposal.operation is ProposalOperation.ACTIVATE
    assert proposal.source_refs == ("observation-001",)
    assert proposal.base_cognitive_revision == 0
    assert proposal.world_revision == 1


def test_invalid_proposal_operation_is_rejected():
    with pytest.raises(ValueError, match="Unsupported proposal operation"):
        CognitiveUpdateProposal(
            proposal_id="proposal-001",
            agent_id="lin-xia",
            target_layer="working_memory",
            operation="delete",
            source_refs=("observation-001",),
            reason="Invalid operation test.",
            base_cognitive_revision=0,
            world_revision=1,
        )


@pytest.mark.parametrize(
    ("model", "field_name"),
    [
        ("world_event", "world_revision"),
        ("proposal_base", "base_cognitive_revision"),
        ("proposal_world", "world_revision"),
    ],
)
def test_negative_revision_is_rejected(model, field_name):
    if model == "world_event":
        with pytest.raises(ValueError, match="non-negative"):
            WorldEvent("e", "b", "w", "BREAK_OBJECT", "a", {}, -1)
        return

    revisions = {"base_cognitive_revision": 0, "world_revision": 0}
    revisions[field_name] = -1
    with pytest.raises(ValueError, match="non-negative"):
        CognitiveUpdateProposal(
            "p", "a", "working_memory", ProposalOperation.CREATE,
            ("observation-001",), "Negative revision test.", **revisions,
        )


def test_domain_records_and_nested_event_payload_are_immutable():
    event = WorldEvent("e", "b", "w", "BREAK_OBJECT", "a", {"details": ["cup"]}, 1)
    observation = ObservationRecord("o", "a", ("e",), "now", "visual", "A cup broke.", 0)
    proposal = CognitiveUpdateProposal(
        "p", "a", "working_memory", ProposalOperation.ACTIVATE,
        ("o",), "Relevant observation.", 0, 1,
    )

    with pytest.raises(FrozenInstanceError):
        event.world_revision = 2
    with pytest.raises(TypeError):
        event.payload["object_id"] = "other"
    with pytest.raises(TypeError):
        event.payload["details"][0] = "other"
    with pytest.raises(FrozenInstanceError):
        observation.agent_id = "another-agent"
    with pytest.raises(FrozenInstanceError):
        proposal.operation = ProposalOperation.UPDATE
