from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.action_decision import (
    ActionDecisionEngine,
    ActionDecisionInput,
)
from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.character import CharacterState


def context_for(role):
    character = CharacterState("agent-1", "角色", role, (), (), (), ())
    return AgentContext("agent-1", character, (), (), {})


def test_doctor_generates_help_candidate_for_patient_situation():
    engine = ActionDecisionEngine(action_id_factory=lambda: "act-help")

    candidates = engine.generate(ActionDecisionInput(context_for("医生"), "病人受伤了"))

    help_action = candidates[0]
    assert help_action.intent == "help"
    assert help_action.motivation == "compassion"
    assert help_action.actor_id == "agent-1"
    assert help_action.action_id == "act-help"


def test_soldier_generates_protect_candidate_for_danger():
    candidates = ActionDecisionEngine().generate(
        ActionDecisionInput(context_for("士兵"), "敌人发起攻击，周围很危险")
    )

    assert candidates[0].intent == "protect"
    assert candidates[0].motivation == "duty"


def test_unknown_situation_generates_observe_candidate():
    candidates = ActionDecisionEngine().generate(
        ActionDecisionInput(context_for("普通居民"), "街道上很安静")
    )

    assert len(candidates) == 1
    assert candidates[0].intent == "observe"
    assert candidates[0].motivation == "curiosity"


def test_action_candidate_and_decision_input_are_immutable():
    candidate = ActionDecisionEngine().generate(
        ActionDecisionInput(context_for("医生"), "有人受伤")
    )[0]
    with pytest.raises(FrozenInstanceError):
        candidate.intent = "leave"

    decision_input = ActionDecisionInput(context_for("医生"), "有人受伤")
    with pytest.raises(FrozenInstanceError):
        decision_input.situation = "changed"

    field_based = ActionCandidate(
        action_id="act-direct",
        actor_id="agent-1",
        intent="help",
        target=None,
        motivation="compassion",
    )
    assert field_based.action_type == "help"


def test_matching_situation_returns_specific_and_general_candidates():
    candidates = ActionDecisionEngine().generate(
        ActionDecisionInput(context_for("医生"), "救助受伤病人")
    )

    assert isinstance(candidates, tuple)
    assert all(isinstance(candidate, ActionCandidate) for candidate in candidates)
    assert tuple(candidate.intent for candidate in candidates) == ("help", "observe")
    assert len({candidate.action_id for candidate in candidates}) == 2


@pytest.mark.parametrize("situation", ["", " "])
def test_empty_situation_is_rejected(situation):
    with pytest.raises(ValueError, match="situation"):
        ActionDecisionInput(context_for("医生"), situation)
