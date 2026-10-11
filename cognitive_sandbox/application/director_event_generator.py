from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from cognitive_sandbox.domain.director_command import DirectorCommand
from cognitive_sandbox.domain.world_events import WorldEvent


class DirectorEventGenerator:
    """Convert supported external director commands into uncommitted events."""

    _EVENT_TYPES = {
        "environment_change": "director_environment_change",
        "add_pressure": "director_pressure",
        "create_event": "director_custom_event",
    }

    def __init__(
        self,
        *,
        world_id: str = "default-world",
        branch_id: str = "main",
        world_revision: int = 0,
        event_id_factory: Callable[[], str] | None = None,
    ) -> None:
        for name, value in (("world_id", world_id), ("branch_id", branch_id)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if isinstance(world_revision, bool) or not isinstance(world_revision, int):
            raise TypeError("world_revision must be a non-negative integer.")
        if world_revision < 0:
            raise ValueError("world_revision must be non-negative.")
        self._world_id = world_id
        self._branch_id = branch_id
        self._world_revision = world_revision
        self._event_id_factory = event_id_factory or (lambda: f"event_{uuid4().hex}")

    def generate(self, command: DirectorCommand) -> WorldEvent | None:
        if not isinstance(command, DirectorCommand):
            raise TypeError("command must be a DirectorCommand.")
        event_type = self._EVENT_TYPES.get(command.command_type)
        if event_type is None:
            return None
        event_id = self._event_id_factory()
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("event_id_factory must return a non-empty string.")
        return WorldEvent(
            event_id=event_id,
            branch_id=self._branch_id,
            world_id=self._world_id,
            event_type=event_type,
            actor_id="director",
            payload=command.payload,
            world_revision=self._world_revision,
        )
