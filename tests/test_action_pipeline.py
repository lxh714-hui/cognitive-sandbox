from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.action_generator import ActionGenerator
from cognitive_sandbox.application.action_selector import ActionSelector
from cognitive_sandbox.domain.actions import ActionCandidate, ActionScore
from cognitive_sandbox.domain.cognition import AgentCognitiveState, EmotionState, WorkingMemoryItem


def _candidate(action_type, target_refs, metadata=None):
    return ActionCandidate(action_type, target_refs, metadata or {})


def test_action_candidate_is_immutable_and_freezes_metadata():
    candidate = _candidate("INSPECT_OBJECT", ("cup_001",), {"nested": {"value": 1}})

    with pytest.raises(FrozenInstanceError):
        candidate.action_type = "WAIT"
    with pytest.raises(TypeError):
        candidate.metadata["new"] = True
    with pytest.raises(TypeError):
        candidate.metadata["nested"]["value"] = 2


def test_action_generator_produces_candidate_without_constructing_proposal():
    state = AgentCognitiveState(
        agent_id="lin-xia",
        working_memory=(
            WorkingMemoryItem(
                item_id="wm-1",
                agent_id="lin-xia",
                content={
                    "text": "liang-jing broke object cup_001.",
                    "world_id": "harbor",
                    "branch_id": "main",
                    "world_revision": 3,
                    "observation_id": "obs-1",
                    "source_event_ids": ("event-1",),
                },
                source_refs=("obs-1",),
                priority=1.0,
                created_at="2026-10-11T12:00:00+00:00",
            ),
        ),
        emotion_state=EmotionState(valence=-0.2, arousal=0.25),
    )

    [candidate] = ActionGenerator().generate(state)

    assert candidate.action_type == "INSPECT_OBJECT"
    assert candidate.target_refs == ("cup_001",)
    assert candidate.metadata["world_id"] == "harbor"
    assert candidate.metadata["decision_rule"] == "inspect_object_after_observing_damage"
    assert candidate.metadata["source_working_memory_item_id"] == "wm-1"
    assert "proposal_id" not in candidate.metadata


def test_action_selector_chooses_highest_score_and_checks_pairing():
    inspect = _candidate("INSPECT_OBJECT", ("cup_001",))
    wait = _candidate("WAIT", ())
    scores = [
        ActionScore("INSPECT_OBJECT", 0.4, ("evidence",)),
        ActionScore("WAIT", 0.7, ("goal",)),
    ]

    assert ActionSelector().select([inspect, wait], scores) == (wait, scores[1])
    assert ActionSelector().select([], []) is None
    with pytest.raises(ValueError, match="exactly one score"):
        ActionSelector().select([inspect], [])
    with pytest.raises(ValueError, match="match by position"):
        ActionSelector().select([inspect], [scores[1]])
