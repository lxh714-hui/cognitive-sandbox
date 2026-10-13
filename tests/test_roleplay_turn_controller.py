from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.roleplay_turn_controller import RoleplayTurnController
from cognitive_sandbox.application.player_action_parser import PlayerActionParser
from cognitive_sandbox.domain.player_action import PlayerAction
from cognitive_sandbox.domain.roleplay_turn import RoleplayTurn


def _controller():
    return RoleplayTurnController(
        PlayerActionParser(entity_aliases={"医生": "doctor", "士兵": "soldier"}),
        turn_id_factory=lambda: "turn-1",
    )


def test_create_turn_starts_waiting_for_input():
    turn = _controller().create_turn("player-1")

    assert turn == RoleplayTurn("turn-1", "player-1", "waiting_input")


def test_submit_input_returns_input_ready_snapshot_without_mutating_original():
    controller = _controller()
    original = controller.create_turn("player-1")

    submitted = controller.submit_input(original, "帮助医生")

    assert submitted.status == "input_ready"
    assert submitted.player_input == "帮助医生"
    assert original.status == "waiting_input"
    assert original.player_input is None


def test_confirm_turn_parses_action_and_sets_executing_status():
    controller = _controller()
    turn = controller.submit_input(controller.create_turn("player-1"), "帮助医生")

    action = controller.confirm_turn(turn)

    assert action == PlayerAction("player-1", "帮助医生", "help", "doctor")
    assert controller.get_turn(turn.turn_id).status == "executing"
    assert turn.status == "input_ready"


def test_complete_turn_transitions_to_completed():
    controller = _controller()
    turn = controller.submit_input(controller.create_turn("player-1"), "观察周围")
    controller.confirm_turn(turn)

    completed = controller.complete_turn(turn)

    assert completed.status == "completed"
    assert completed.player_input == "观察周围"
    assert controller.get_turn(turn.turn_id) == completed


def test_confirm_without_input_fails_and_keeps_waiting_state():
    controller = _controller()
    turn = controller.create_turn("player-1")

    with pytest.raises(ValueError, match="without submitted input"):
        controller.confirm_turn(turn)
    assert controller.get_turn(turn.turn_id) == turn


def test_turn_snapshots_are_immutable():
    turn = _controller().create_turn("player-1")

    with pytest.raises(FrozenInstanceError):
        turn.status = "executing"


def test_player_can_revise_input_before_confirmation():
    controller = _controller()
    initial = controller.create_turn("player-1")
    first = controller.submit_input(initial, "看看门外")
    revised = controller.submit_input(first, "保护士兵")

    assert first.player_input == "看看门外"
    assert revised.player_input == "保护士兵"
    assert controller.confirm_turn(revised).intent == "protect"
