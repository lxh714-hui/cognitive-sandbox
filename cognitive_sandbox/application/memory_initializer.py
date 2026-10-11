from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from cognitive_sandbox.domain.memory import InitialMemory


class MemoryInitializer:
    """Create a small, static past-memory template from a role description."""

    def __init__(self, *, memory_id_factory: Callable[[], str] | None = None) -> None:
        self._memory_id_factory = memory_id_factory or (lambda: f"memory_{uuid4().hex}")

    def initialize(self, role_description: str) -> tuple[InitialMemory, ...]:
        if not isinstance(role_description, str) or not role_description.strip():
            raise ValueError("role_description must not be empty.")

        description = role_description.casefold()
        if "医生" in description:
            content, importance = "曾经帮助过一名病人", 0.5
        elif "士兵" in description:
            content, importance = "经历过一次战斗", 0.7
        else:
            return ()

        memory_id = self._memory_id_factory()
        if not isinstance(memory_id, str) or not memory_id.strip():
            raise ValueError("memory_id_factory must return a non-empty string.")
        return (InitialMemory(memory_id, content, importance),)
