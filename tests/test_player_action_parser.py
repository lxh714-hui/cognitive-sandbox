from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.player_action_parser import PlayerActionParser
from cognitive_sandbox.domain.player_action import PlayerAction


@pytest.mark.parametrize("text", ["观察周围", "看看门外", "查看桌上的杯子"])
def test_observation_keywords_create_observe_action(text):
    action = PlayerActionParser().parse("player-1", text)

    assert action.intent == "observe"
    assert action.raw_input == text
    assert action.player_id == "player-1"


@pytest.mark.parametrize("text", ["帮助医生", "救一下受伤的人"])
def test_help_keywords_create_help_action(text):
    action = PlayerActionParser().parse("player-1", text)

    assert action.intent == "help"


@pytest.mark.parametrize("text", ["保护士兵", "守护入口"])
def test_protect_keywords_create_protect_action(text):
    action = PlayerActionParser().parse("player-1", text)

    assert action.intent == "protect"


def test_target_is_detected_from_role_keywords():
    parser = PlayerActionParser(entity_aliases={"医生": "doctor", "士兵": "soldier"})

    assert parser.parse("player-1", "帮助医生").target == "doctor"
    assert parser.parse("player-1", "保护士兵").target == "soldier"
    assert parser.parse("player-1", "保护入口").target is None


def test_unrecognized_input_returns_none():
    parser = PlayerActionParser()

    assert parser.parse("player-1", "我想休息") is None
    assert parser.parse("player-1", "   ") is None


def test_player_action_is_immutable():
    action = PlayerActionParser().parse("player-1", "观察")

    with pytest.raises(FrozenInstanceError):
        action.intent = "help"


def test_player_action_validates_required_fields():
    with pytest.raises(ValueError, match="player_id"):
        PlayerAction(" ", "观察", "observe")
    with pytest.raises(ValueError, match="raw_input"):
        PlayerAction("player-1", " ", "observe")
