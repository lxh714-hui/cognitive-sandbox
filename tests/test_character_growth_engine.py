from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.character_growth_engine import CharacterGrowthEngine
from cognitive_sandbox.domain.agent_state import AgentDynamicState
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.domain.character_development import CharacterDevelopmentState
from cognitive_sandbox.domain.memory import InitialMemory


def _character():
    return CharacterState("agent-1", "林夏", "医生", ("谨慎",), ("帮助他人",), (), ())


def _dynamic():
    return AgentDynamicState("agent-1", 0.6, 0.2, 0.7)


def _memory(memory_id, content):
    return InitialMemory(memory_id, content, 0.5)


def test_help_memory_generates_compassion_and_helping_values():
    state = CharacterGrowthEngine().evaluate(
        _character(), (_memory("m1", "我曾经帮助过他人"),), _dynamic()
    )

    assert state.trait_growth == ("compassion_strengthened",)
    assert state.value_growth == ("helping_others",)
    assert state.experience_count == 1


def test_protect_memory_generates_protective_and_responsibility_growth():
    state = CharacterGrowthEngine().evaluate(
        _character(), (_memory("m1", "我曾经保护过目标"),), _dynamic()
    )

    assert state.trait_growth == ("protective",)
    assert state.value_growth == ("responsibility",)


def test_failure_memory_generates_resilience():
    state = CharacterGrowthEngine().evaluate(
        _character(), (_memory("m1", "我曾经经历过一次失败的行动"),), _dynamic()
    )

    assert state.trait_growth == ("resilience",)
    assert state.value_growth == ()


def test_multiple_memories_merge_growth_signals_in_order():
    memories = (
        _memory("m1", "帮助过一位病人"),
        _memory("m2", "保护过同伴"),
        _memory("m3", "经历失败后继续努力"),
    )

    state = CharacterGrowthEngine().evaluate(_character(), memories, _dynamic())

    assert state.trait_growth == (
        "compassion_strengthened",
        "protective",
        "resilience",
    )
    assert state.value_growth == ("helping_others", "responsibility")
    assert state.experience_count == 3


def test_duplicate_growth_labels_are_deduplicated():
    memories = (
        _memory("m1", "帮助过一位病人"),
        _memory("m2", "再次帮助其他人"),
        _memory("m3", "保护并帮助同伴"),
    )

    state = CharacterGrowthEngine().evaluate(_character(), memories, _dynamic())

    assert state.trait_growth.count("compassion_strengthened") == 1
    assert state.trait_growth.count("protective") == 1
    assert state.value_growth.count("helping_others") == 1


def test_empty_memory_is_supported():
    state = CharacterGrowthEngine().evaluate(_character(), (), _dynamic())

    assert state == CharacterDevelopmentState("agent-1", (), (), 0)


def test_growth_evaluation_does_not_mutate_input_states():
    character = _character()
    dynamic = _dynamic()
    memories = (_memory("m1", "帮助过一位病人"),)
    original_traits, original_memories = character.traits, memories

    CharacterGrowthEngine().evaluate(character, memories, dynamic)

    assert character.traits == original_traits
    assert memories == original_memories
    assert dynamic == AgentDynamicState("agent-1", 0.6, 0.2, 0.7)


def test_development_state_is_immutable_and_normalizes_to_tuples():
    state = CharacterDevelopmentState("agent-1", ["resilience"], ["helping_others"], 1)

    assert state.trait_growth == ("resilience",)
    assert state.value_growth == ("helping_others",)
    with pytest.raises(FrozenInstanceError):
        state.experience_count = 2
