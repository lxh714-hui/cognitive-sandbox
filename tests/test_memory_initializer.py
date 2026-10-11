from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.memory_initializer import MemoryInitializer
from cognitive_sandbox.domain.memory import InitialMemory


def test_doctor_gets_initial_memory():
    memories = MemoryInitializer(memory_id_factory=lambda: "memory-doctor").initialize("医生")

    assert memories == (InitialMemory("memory-doctor", "曾经帮助过一名病人", 0.5),)


def test_soldier_gets_initial_memory():
    memories = MemoryInitializer(memory_id_factory=lambda: "memory-soldier").initialize("士兵")

    assert memories == (InitialMemory("memory-soldier", "经历过一次战斗", 0.7),)


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
