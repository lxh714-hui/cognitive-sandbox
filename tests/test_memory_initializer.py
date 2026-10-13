from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.memory_initializer import MemoryInitializer
from cognitive_sandbox.domain.memory import InitialMemory


def test_scenario_memory_template_is_copied_without_role_inference():
    memories = MemoryInitializer(memory_id_factory=lambda: "memory-configured").initialize(
        "角色", templates=({"content": "既有经历", "importance": 0.5},),
    )

    assert memories == (InitialMemory("memory-configured", "既有经历", 0.5),)


def test_role_without_configured_memories_starts_with_no_inferred_biography():
    memories = MemoryInitializer(memory_id_factory=lambda: "memory-role").initialize("角色")

    assert memories == ()


def test_unknown_role_has_no_initial_memories():
    assert MemoryInitializer().initialize("普通居民") == ()


@pytest.mark.parametrize("importance", [-0.1, 1.1])
def test_initial_memory_importance_must_be_in_range(importance):
    with pytest.raises(ValueError, match="importance"):
        InitialMemory("memory-1", "曾经发生的事", importance)


def test_initial_memory_is_immutable_and_rejects_empty_content():
    memory = InitialMemory("memory-1", "帮助过一名病人", 0.5)
    with pytest.raises(FrozenInstanceError):
        memory.content = "changed"
    with pytest.raises(ValueError, match="content"):
        InitialMemory("memory-2", " ", 0.5)
