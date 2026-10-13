from __future__ import annotations

from cognitive_sandbox.domain.world_instance import WorldInstance
from cognitive_sandbox.persistence.models.save_metadata import SaveMetadata
from cognitive_sandbox.persistence.world_serializer import WorldSerializer


class WorldSaveError(ValueError):
    """A save could not be safely read or written."""


class WorldSaveService:
    """Application boundary for saving and restoring complete world snapshots."""

    def __init__(self, repository, serializer: WorldSerializer | None = None) -> None:
        if not all(callable(getattr(repository, name, None)) for name in (
            "save_world", "load_world", "list_worlds", "delete_world"
        )):
            raise TypeError("repository must implement the SaveRepository interface.")
        self.repository = repository
        self.serializer = serializer or WorldSerializer()
        self._errors: dict[str, str] = {}

    @property
    def errors(self) -> dict[str, str]:
        return dict(self._errors)

    def save_world(
        self,
        world: WorldInstance,
        session,
        *,
        created_time: str,
        messages=(),
        patches=(),
        character_minds=None,
        knowledge_facts=(),
        knowledge_records=(),
        timeline=None,
        relationships=None,
    ) -> None:
        if not isinstance(world, WorldInstance):
            raise TypeError("world must be a WorldInstance.")
        metadata = SaveMetadata(
            instance_id=world.instance_id,
            world_id=world.world_id,
            scenario_id=world.scenario_id,
            name=world.name,
            description=world.description,
            created_time=created_time,
            last_played_time=world.last_played,
            status=world.status,
            world_status=world.world_status,
            player_character_id=world.player_character_id or getattr(session, "player_character_id", session.player_id),
        )
        try:
            document = self.serializer.serialize_world(
                metadata,
                session,
                messages=messages,
                patches=patches,
                character_minds=character_minds,
                knowledge_facts=knowledge_facts,
                knowledge_records=knowledge_records,
                timeline=timeline,
                relationships=relationships,
            )
            self.repository.save_world(world.instance_id, document)
        except Exception as error:
            self._errors[world.instance_id] = f"存档保存失败：{error}"
            raise WorldSaveError(self._errors[world.instance_id]) from error
        self._errors.pop(world.instance_id, None)

    def load_world(self, instance_id: str) -> dict:
        try:
            decoded = self.serializer.deserialize_world(self.repository.load_world(instance_id))
        except Exception as error:
            message = f"世界存档无法读取：{instance_id}（{error}）"
            self._errors[instance_id] = message
            raise WorldSaveError(message) from error
        self._errors.pop(instance_id, None)
        return decoded

    def list_worlds(self) -> tuple[SaveMetadata, ...]:
        self._errors.clear()
        worlds = []
        for instance_id in self.repository.list_worlds():
            try:
                decoded = self.serializer.deserialize_world(self.repository.load_world(instance_id))
                metadata = decoded["metadata"]
                if metadata.instance_id != instance_id:
                    raise ValueError("save filename and instance identity differ.")
                worlds.append(metadata)
            except Exception as error:
                self._errors[instance_id] = f"存档损坏或无法读取：{instance_id}（{error}）"
        return tuple(worlds)

    def list_instance_ids(self) -> tuple[str, ...]:
        """List stored identifiers, including damaged saves, to prevent accidental overwrite."""
        return tuple(self.repository.list_worlds())

    def delete_world(self, instance_id: str) -> bool:
        result = self.repository.delete_world(instance_id)
        self._errors.pop(instance_id, None)
        return result
