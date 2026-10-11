from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.action_scorer import ActionScorer
from cognitive_sandbox.domain.actions import ActionCandidate, ActionScore
from cognitive_sandbox.domain.cognition import (
    AgentCognitiveState,
    Belief,
    EmotionState,
    Goal,
    LongTermMemory,
    Relationship,
    WorkingMemoryItem,
)


def _candidate(action_type, target_id=None):
    return ActionCandidate(
        action_type=action_type,
        target_refs=(target_id,) if target_id else (),
        metadata={},
    )


def test_action_score_is_immutable_and_bounded():
    score = ActionScore("INSPECT_OBJECT", 0.8, ("supported_by_belief",))

    with pytest.raises(FrozenInstanceError):
        score.score = 0.2
    with pytest.raises(ValueError, match="between 0 and 1"):
        ActionScore("INSPECT_OBJECT", 1.1, ())


def test_action_scorer_combines_cognition_emotion_goals_and_relationships():
    state = AgentCognitiveState(
        agent_id="lin-xia",
        working_memory=(
            WorkingMemoryItem(
                item_id="wm-1",
                agent_id="lin-xia",
                content={"text": "看到物体 cup_001 碎裂"},
                source_refs=("observation-1",),
                priority=1.0,
                created_at="2026-10-11T12:00:00+00:00",
            ),
        ),
        emotion_state=EmotionState(valence=-0.5, arousal=0.5),
        beliefs=(
            Belief(
                belief_id="belief-1",
                agent_id="lin-xia",
                belief_type="perceptual",
                proposition="物体 cup_001 碎裂",
                confidence=0.8,
                source_refs=("observation-1",),
            ),
        ),
    )
    goals = (
        Goal("goal-1", "lin-xia", "investigate", "Investigate the cup", 0.6, "active", ("obs-2",)),
    )
    relationships = (
        Relationship("rel-1", "lin-xia", "liang-jing", 0.8, 0.7, 0.1, ("obs-3",)),
    )
    memories = (
        LongTermMemory(
            "memory-1",
            "lin-xia",
            "episodic",
            {"text": "cup_001 broke"},
            ("observation-4",),
            0.9,
            "2026-10-11T11:00:00+00:00",
        ),
    )

    inspect, wait = ActionScorer().score(
        state,
        [_candidate("INSPECT_OBJECT", "cup_001"), _candidate("WAIT")],
        goals=goals,
        relationships=relationships,
        memories=memories,
    )

    assert inspect.action_type == "INSPECT_OBJECT"
    assert inspect.score == pytest.approx(0.7685)
    assert {
        "supported_by_working_memory",
        "supported_by_belief",
        "supported_by_long_term_memory",
        "emotion_signal",
        "active_goal_match",
        "high_trust_relationship",
    }.issubset(inspect.reasons)
    assert wait.action_type == "WAIT"
    assert inspect.score > wait.score


def test_action_scorer_rejects_other_agents_private_state():
    state = AgentCognitiveState(agent_id="lin-xia")
    relationship = Relationship("rel-1", "liang-jing", "lin-xia", 0.9, 0.5, 0.1, ("obs-1",))

    with pytest.raises(ValueError, match="outgoing"):
        ActionScorer().score(
            state,
            [_candidate("WAIT")],
            relationships=(relationship,),
        )
