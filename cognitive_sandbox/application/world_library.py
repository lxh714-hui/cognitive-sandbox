from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

from cognitive_sandbox.application.roleplay_session import RoleplaySession
from cognitive_sandbox.domain.world_instance import WorldInstance


@dataclass
class _WorldRecord:
    session: RoleplaySession
    item: WorldInstance
    messages: tuple[Any, ...]
    snapshot: tuple[dict[str, Any], Any, Any, Any]
    patches: tuple[Any, ...] = ()
    created_time: str = ""


class WorldLibrary:
    """Keep world instances and their roleplay snapshots isolated in this app run."""

    def __init__(self, save_service=None, session_loader=None) -> None:
        self._records: dict[str, _WorldRecord] = {}
        self._active_id: str | None = None
        self._save_service = None
        self._session_loader = None
        self.persistence_errors: dict[str, str] = {}
        if save_service is not None:
            self.configure_persistence(save_service, session_loader)

    def configure_persistence(self, save_service, session_loader) -> None:
        if not callable(getattr(save_service, "save_world", None)) or not callable(
            getattr(save_service, "list_worlds", None)
        ):
            raise TypeError("save_service must provide save_world() and list_worlds().")
        if not callable(session_loader):
            raise TypeError("session_loader must be callable.")
        self._save_service = save_service
        self._session_loader = session_loader
        self.persistence_errors = dict(getattr(save_service, "errors", {}))

    @property
    def active_id(self) -> str | None:
        return self._active_id

    def register(self, session: RoleplaySession) -> WorldInstance:
        if not isinstance(session, RoleplaySession):
            raise TypeError("session must be a RoleplaySession.")
        instance_id = getattr(session, "world_instance_id", None) or f"world_{uuid4().hex}"
        list_instance_ids = getattr(self._save_service, "list_instance_ids", None)
        if self._save_service is None:
            persisted_ids = set()
        elif callable(list_instance_ids):
            persisted_ids = set(list_instance_ids())
        else:
            persisted_ids = {metadata.instance_id for metadata in self._save_service.list_worlds()}
        if instance_id in self._records or instance_id in persisted_ids:
            raise ValueError(f"world instance already exists: {instance_id}")
        session.world_instance_id = instance_id
        scenario = getattr(session, "scenario", None)
        content = getattr(session, "scenario_content", None)
        world = getattr(content, "world_document", None) if content is not None else None
        scenario_id = getattr(scenario, "scenario_id", "custom") or "custom"
        name = getattr(world, "name", "") or getattr(scenario, "name", "") or "未命名世界"
        description = (
            getattr(world, "description", "")
            or getattr(scenario, "description", "")
            or "暂无世界简介。"
        )
        now = self._now()
        world_id = getattr(session, "world_instance_id", instance_id) or instance_id
        item = WorldInstance(
            instance_id=instance_id,
            scenario_id=scenario_id,
            world_id=world_id,
            name=name,
            description=description,
            status="当前世界",
            world_status=self._describe_state(session.world_state),
            last_played=now,
            player_character_id=getattr(session, "player_character_id", session.player_id),
        )
        self._records[instance_id] = _WorldRecord(
            session=session,
            item=item,
            messages=(),
            snapshot=self._capture(session),
            created_time=now,
        )
        self._mark_active(instance_id)
        return item

    def list_worlds(self) -> tuple[WorldInstance, ...]:
        in_memory = [record.item for record in self._records.values()]
        if self._save_service is None:
            return tuple(in_memory)
        saved_items = []
        for metadata in self._save_service.list_worlds():
            if metadata.instance_id in self._records:
                continue
            saved_items.append(self._from_metadata(metadata))
        self.persistence_errors = dict(getattr(self._save_service, "errors", {}))
        return (*in_memory, *saved_items)

    def messages_for(self, instance_id: str) -> tuple[Any, ...]:
        return self._record(instance_id).messages

    def patches_for(self, instance_id: str) -> tuple[Any, ...]:
        """Return world-local, append-only patches without touching runtime state."""
        return self._record(instance_id).patches

    def append_patch(self, instance_id: str, patch) -> None:
        from cognitive_sandbox.domain.world_patch import WorldPatch

        if not isinstance(patch, WorldPatch):
            raise TypeError("patch must be a WorldPatch.")
        record = self._record(instance_id)
        if any(existing.id == patch.id for existing in record.patches):
            raise ValueError(f"world patch already exists: {patch.id}")
        record.patches = (*record.patches, patch)
        self._persist(record)

    def character_ids_for(self, instance_id: str) -> tuple[str, ...]:
        record = self._record(instance_id)
        content = getattr(record.session, "scenario_content", None)
        identifiers = [card.character_id for card in getattr(content, "character_cards", ())]
        from cognitive_sandbox.domain.world_patch import CharacterAddition, WorldPatchType
        for patch in record.patches:
            if patch.type is WorldPatchType.CHARACTER_ADDITION and isinstance(patch.payload, CharacterAddition):
                identifiers.append(patch.payload.character_card.character_id)
        return tuple(identifiers)

    def historical_facts_for(self, instance_id: str) -> tuple[str, ...]:
        record = self._record(instance_id)
        content = getattr(record.session, "scenario_content", None)
        world = getattr(content, "world_document", None)
        facts = [*getattr(world, "history", ()), *getattr(world, "rules", ())]
        state = record.session.world_state
        for key in ("history", "rules", "facts"):
            values = state.get(key, ()) if hasattr(state, "get") else ()
            if isinstance(values, (tuple, list)):
                facts.extend(item for item in values if isinstance(item, str))
        return tuple(facts)

    def current_day_for(self, instance_id: str) -> int | None:
        state = self._record(instance_id).session.world_state
        for key in ("day", "current_day", "world_day"):
            value = state.get(key) if hasattr(state, "get") else None
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                return value
        return None

    def summary_for(self, instance_id: str) -> dict[str, Any]:
        """Return display-safe package and recent activity metadata for lobby cards."""
        record = self._records.get(instance_id)
        if record is None:
            item = next((world for world in self.list_worlds() if world.instance_id == instance_id), None)
            if item is None:
                return {}
            return {"version": "未标注", "character_count": "—", "day": None,
                    "recent_summary": item.world_status or "尚无近期事件"}
        session = record.session
        version = getattr(session, "scenario_version", None)
        cards = getattr(getattr(session, "scenario_content", None), "character_cards", ())
        events = getattr(getattr(getattr(session, "executor", None), "event_timeline", None), "events", ())
        recent = next((event.metadata.get("public_description") or event.metadata.get("description")
                       for event in reversed(events)
                       if isinstance(event.metadata.get("public_description") or event.metadata.get("description"), str)), None)
        return {"version": version or "未标注", "character_count": len(cards),
                "day": self.current_day_for(instance_id), "recent_summary": recent or "尚无近期事件"}

    def active_session(self) -> RoleplaySession | None:
        if self._active_id is None:
            return None
        return self._records[self._active_id].session

    def save_active(self, messages: tuple[Any, ...] | list[Any]) -> None:
        if self._active_id is None:
            return
        if any(not hasattr(message, "message_type") or not hasattr(message, "content") for message in messages):
            raise TypeError("messages must contain display message values.")
        record = self._records[self._active_id]
        record.messages = tuple(messages)
        record.snapshot = self._capture(record.session)
        record.item = self._updated_item(record.item, record.session, "当前世界")
        self._persist(record)

    def deactivate(self, current_messages: tuple[Any, ...] | list[Any] = ()) -> None:
        """Save the active world and return the library to an unselected state."""
        if self._active_id is None:
            return True
        instance_id = self._active_id
        self.save_active(current_messages)
        if instance_id in self.persistence_errors:
            return False
        record = self._records[instance_id]
        record.item = self._updated_item(record.item, record.session, "可继续")
        self._persist(record)
        if instance_id in self.persistence_errors:
            return False
        self._active_id = None
        return True

    def activate(
        self,
        instance_id: str,
        current_messages: tuple[Any, ...] | list[Any] = (),
    ) -> tuple[RoleplaySession, tuple[Any, ...]]:
        if instance_id not in self._records:
            self._load_persisted(instance_id)
        if self._active_id is not None:
            self.save_active(current_messages)
        target = self._records[instance_id]
        self._restore(target.session, target.snapshot)
        self._mark_active(instance_id)
        target.item = self._updated_item(target.item, target.session, "当前世界")
        self._persist(target)
        return target.session, target.messages

    def delete_world(self, instance_id: str) -> bool:
        if self._active_id == instance_id:
            raise ValueError("cannot delete the active world instance.")
        existed = instance_id in self._records
        removed = False
        if self._save_service is not None:
            removed = self._save_service.delete_world(instance_id)
        self._records.pop(instance_id, None)
        return existed or removed

    def _mark_active(self, instance_id: str) -> None:
        if self._active_id is not None and self._active_id in self._records:
            previous = self._records[self._active_id]
            previous.item = self._updated_item(previous.item, previous.session, "可继续")
            self._persist(previous)
        self._active_id = instance_id
        current = self._records[instance_id]
        current.item = self._updated_item(current.item, current.session, "当前世界")
        self._persist(current)

    def _load_persisted(self, instance_id: str) -> None:
        if self._save_service is None or self._session_loader is None:
            raise KeyError(f"unknown world instance: {instance_id}")
        saved = self._save_service.load_world(instance_id)
        try:
            metadata = saved["metadata"]
            session = self._session_loader(saved)
            messages = tuple(saved["messages"])
            patches = tuple(saved["patches"])
            if not isinstance(session, RoleplaySession):
                raise TypeError("restorer did not return a RoleplaySession.")
        except Exception as error:
            from cognitive_sandbox.persistence.world_save_service import WorldSaveError

            message = f"世界存档无法恢复：{instance_id}（{error}）"
            self.persistence_errors[instance_id] = message
            raise WorldSaveError(message) from error
        item = self._from_metadata(metadata)
        self._records[instance_id] = _WorldRecord(
            session=session,
            item=item,
            messages=messages,
            snapshot=self._capture(session),
            patches=patches,
            created_time=metadata.created_time,
        )

    def _persist(self, record: _WorldRecord) -> None:
        if self._save_service is None:
            return
        retriever = getattr(record.session, "knowledge_retriever", None)
        snapshot = getattr(retriever, "snapshot", None)
        facts, knowledge_records = snapshot() if callable(snapshot) else ((), ())
        try:
            self._save_service.save_world(
                record.item,
                record.session,
                created_time=record.created_time or record.item.last_played,
                messages=record.messages,
                patches=record.patches,
                knowledge_facts=facts,
                knowledge_records=knowledge_records,
            )
            self.persistence_errors.pop(record.item.instance_id, None)
        except Exception as error:
            self.persistence_errors[record.item.instance_id] = str(error)

    @staticmethod
    def _from_metadata(metadata) -> WorldInstance:
        return WorldInstance(
            instance_id=metadata.instance_id,
            scenario_id=metadata.scenario_id,
            world_id=metadata.world_id,
            name=metadata.name,
            description=metadata.description,
            status=metadata.status if metadata.status != "当前世界" else "可继续",
            world_status=metadata.world_status,
            last_played=metadata.last_played_time,
            player_character_id=getattr(metadata, "player_character_id", None),
        )

    def _record(self, instance_id: str) -> _WorldRecord:
        try:
            return self._records[instance_id]
        except KeyError as error:
            raise KeyError(f"unknown world instance: {instance_id}") from error

    @staticmethod
    def _capture(session: RoleplaySession) -> tuple[dict[str, Any], Any, Any, Any]:
        return (
            _mutable_snapshot(session.world_state),
            session.agent_context,
            session.current_turn,
            session.last_result,
        )

    @staticmethod
    def _restore(session: RoleplaySession, snapshot: tuple[dict[str, Any], Any, Any, Any]) -> None:
        world_state, agent_context, current_turn, last_result = snapshot
        session.world_state = _mutable_snapshot(world_state)
        session.agent_context = agent_context
        session.current_turn = current_turn
        session.last_result = last_result

    def _updated_item(self, item: WorldInstance, session: RoleplaySession, status: str) -> WorldInstance:
        return WorldInstance(
            instance_id=item.instance_id,
            scenario_id=item.scenario_id,
            world_id=item.world_id,
            name=item.name,
            description=item.description,
            status=status,
            world_status=self._describe_state(session.world_state),
            last_played=self._now(),
            player_character_id=getattr(session, "player_character_id", session.player_id),
        )

    @staticmethod
    def _describe_state(state) -> str:
        if not isinstance(state, dict) and not hasattr(state, "items"):
            return "暂无状态记录"
        labels = {
            "location": "地点",
            "current_location": "地点",
            "danger_level": "危险程度",
            "energy_level": "能源",
            "resource_level": "资源",
        }
        parts: list[str] = []
        for key, label in labels.items():
            if key not in state:
                continue
            value = state[key]
            if isinstance(value, bool) or not isinstance(value, (str, int, float)):
                continue
            if isinstance(value, (int, float)) and key.endswith("_level") and 0 <= value <= 1:
                value = f"{round(value * 100)}%"
            parts.append(f"{label}：{value}")
        return " · ".join(parts) if parts else "暂无状态摘要"

    @staticmethod
    def _now() -> str:
        return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")


def _mutable_snapshot(value):
    from cognitive_sandbox.application.mutable_snapshot import mutable_snapshot

    return mutable_snapshot(value)
