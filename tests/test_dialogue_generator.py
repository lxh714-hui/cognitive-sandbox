from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.dialogue_generator import DialogueGenerator
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.domain.dialogue import DialogueLine


def _agent(agent_id="agent-1", traits=()):
    character = CharacterState(agent_id, "角色", "普通居民", traits, (), (), ())
    return AgentContext(agent_id, character, (), (), {})


def test_compassionate_speaker_generates_help_line():
    line = DialogueGenerator().generate(_agent(traits=("compassionate",)), None, "I can help")

    assert line == DialogueLine("agent-1", "我只是做了应该做的事。", "calm")


def test_brave_speaker_generates_danger_line():
    line = DialogueGenerator().generate(_agent(traits=("brave",)), None, "There is danger")

    assert line == DialogueLine("agent-1", "退后，我来处理。", "determined")


@pytest.mark.parametrize(
    ("traits", "situation"),
    [
        (("compassionate",), "A quiet morning"),
        (("brave",), "I can help"),
        (("curious",), "danger and help"),
    ],
)
def test_unmatched_trait_and_situation_returns_none(traits, situation):
    assert DialogueGenerator().generate(_agent(traits=traits), None, situation) is None


def test_dialogue_line_is_immutable_and_speaker_matches_context():
    line = DialogueGenerator().generate(_agent("speaker-7", ("brave",)), None, "danger")

    assert line.speaker_id == "speaker-7"
    with pytest.raises(FrozenInstanceError):
        line.text = "changed"


def test_dialogue_line_allows_empty_emotion_hint_but_requires_text():
    assert DialogueLine("speaker-1", "Hello", "").emotion_hint == ""
    with pytest.raises(ValueError, match="text"):
        DialogueLine("speaker-1", " ", "calm")
