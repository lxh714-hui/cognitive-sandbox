from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from cognitive_sandbox.domain.memory import InitialMemory


class MemoryInitializer:
    """Copy memory templates supplied by a scenario; never infer biography from a role."""

    def __init__(self, *, memory_id_factory: Callable[[], str] | None = None) -> None:
        self._memory_id_factory = memory_id_factory or (lambda: f"memory_{uuid4().hex}")

    def initialize(self, role_description: str, *, templates=()) -> tuple[InitialMemory, ...]:
        if not isinstance(role_description, str) or not role_description.strip():
            raise ValueError("role_description must not be empty.")

        result = []
        for template in templates:
            content = getattr(template, "content", None)
            importance = getattr(template, "importance", None)
            if isinstance(template, dict):
                content, importance = template.get("content"), template.get("importance", 0.5)
            if not isinstance(content, str) or not content.strip():
                raise ValueError("memory templates require non-empty content.")
            memory_id = self._memory_id_factory()
            if not isinstance(memory_id, str) or not memory_id.strip():
                raise ValueError("memory_id_factory must return a non-empty string.")
            result.append(InitialMemory(memory_id, content, importance))
        return tuple(result)
