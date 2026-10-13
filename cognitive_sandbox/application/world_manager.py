from __future__ import annotations


class WorldLifecycleError(ValueError):
    """A world lifecycle operation is invalid for the current session state."""


class WorldManager:
    """Application boundary for world lifecycle operations."""

    def __init__(self, world_library) -> None:
        if not callable(getattr(world_library, "list_worlds", None)) or not callable(
            getattr(world_library, "delete_world", None)
        ):
            raise TypeError("world_library must provide list_worlds() and delete_world().")
        self.world_library = world_library

    def delete_world(self, instance_id: str) -> bool:
        if not isinstance(instance_id, str) or not instance_id.strip():
            raise ValueError("instance_id must not be empty.")
        if self.world_library.active_id == instance_id:
            raise WorldLifecycleError("当前世界正在运行，退出后才能删除。")
        if not any(world.instance_id == instance_id for world in self.world_library.list_worlds()):
            return False
        return self.world_library.delete_world(instance_id)
