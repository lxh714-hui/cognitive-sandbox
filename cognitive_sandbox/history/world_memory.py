from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from uuid import uuid4


def _freeze(value):
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return tuple(sorted((_freeze(item) for item in value), key=repr))
    return value


def _timestamp(value=None):
    if value is None or value == "":
        return datetime.now(timezone.utc).isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


@dataclass(frozen=True)
class WorldDelta:
    """An append-only description of one already-applied world change."""

    id: str
    timestamp: str
    source: str
    target: str
    change_type: str
    before: object = None
    after: object = None
    cause: str = ""

    def __post_init__(self):
        for name in ("id", "timestamp", "source", "target", "change_type"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        object.__setattr__(self, "before", _freeze(self.before))
        object.__setattr__(self, "after", _freeze(self.after))
        if not isinstance(self.cause, str):
            raise TypeError("cause must be a string.")


@dataclass(frozen=True)
class WorldHistoryRecord:
    """A compact historical fact, separate from executable simulation events."""

    record_id: str
    timestamp: str
    record_type: str
    source_id: str
    summary: str
    metadata: Mapping = field(default_factory=dict)

    def __post_init__(self):
        for name in ("record_id", "timestamp", "record_type", "source_id", "summary"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping.")
        object.__setattr__(self, "metadata", _freeze(self.metadata))


@dataclass(frozen=True)
class WorldHistory:
    event_deltas: tuple[WorldDelta, ...] = ()
    event_history: tuple[WorldHistoryRecord, ...] = ()
    opportunity_history: tuple[WorldHistoryRecord, ...] = ()
    conflict_history: tuple[WorldHistoryRecord, ...] = ()
    decision_history: tuple[WorldHistoryRecord, ...] = ()
    relationship_history: tuple[WorldHistoryRecord, ...] = ()
    world_tree_history: tuple[WorldHistoryRecord, ...] = ()

    def __post_init__(self):
        for name in ("event_deltas", "event_history", "opportunity_history", "conflict_history",
                     "decision_history", "relationship_history", "world_tree_history"):
            values = tuple(getattr(self, name))
            expected = WorldDelta if name == "event_deltas" else WorldHistoryRecord
            if any(not isinstance(item, expected) for item in values):
                raise TypeError(f"{name} contains an invalid world history record.")
            object.__setattr__(self, name, values)


@dataclass(frozen=True)
class WorldMemorySnapshot:
    current_snapshot: Mapping = field(default_factory=dict)
    history: WorldHistory = field(default_factory=WorldHistory)

    def __post_init__(self):
        if not isinstance(self.current_snapshot, Mapping):
            raise TypeError("current_snapshot must be a mapping.")
        if not isinstance(self.history, WorldHistory):
            raise TypeError("history must be WorldHistory.")
        object.__setattr__(self, "current_snapshot", _freeze(self.current_snapshot))


class WorldMemory:
    """Append-only recorder. It observes notifications and never applies changes."""

    def __init__(self, snapshot: WorldMemorySnapshot | None = None):
        snapshot = snapshot or WorldMemorySnapshot()
        if not isinstance(snapshot, WorldMemorySnapshot):
            raise TypeError("snapshot must be WorldMemorySnapshot.")
        self._current_snapshot = dict(snapshot.current_snapshot)
        history = snapshot.history
        self._histories = {
            "event_deltas": list(history.event_deltas),
            "event_history": list(history.event_history),
            "opportunity_history": list(history.opportunity_history),
            "conflict_history": list(history.conflict_history),
            "decision_history": list(history.decision_history),
            "relationship_history": list(history.relationship_history),
            "world_tree_history": list(history.world_tree_history),
        }
        self._recorded_events = {item.source_id for item in history.event_history}

    @classmethod
    def restore(cls, snapshot):
        return cls(snapshot)

    @property
    def current_snapshot(self):
        return _freeze(self._current_snapshot)

    @property
    def event_deltas(self):
        return tuple(self._histories["event_deltas"])

    @property
    def history(self):
        return WorldHistory(**{key: tuple(value) for key, value in self._histories.items()})

    def set_current_snapshot(self, snapshot: Mapping) -> None:
        if not isinstance(snapshot, Mapping):
            raise TypeError("snapshot must be a mapping.")
        self._current_snapshot = dict(_freeze(snapshot))

    def snapshot(self) -> WorldMemorySnapshot:
        return WorldMemorySnapshot(self._current_snapshot, self.history)

    def record_delta(self, *, source, target, change_type, before=None, after=None,
                     cause="", timestamp=None, record_id=None):
        delta = WorldDelta(record_id or f"delta_{uuid4().hex}", _timestamp(timestamp), str(source),
                           str(target), str(change_type), before, after, cause)
        self._histories["event_deltas"].append(delta)
        return delta

    def record_event(self, event, context=None):
        event_id = str(getattr(event, "event_id", ""))
        if not event_id or event_id in self._recorded_events:
            return None
        event_type = str(getattr(event, "event_type", "world_event"))
        payload = getattr(event, "payload", {}) or {}
        actor = getattr(event, "actor_id", None) or "world"
        target = getattr(event, "target_id", None) or "world"
        timestamp = getattr(event, "timestamp", None) or _timestamp()
        description = payload.get("description", "") if isinstance(payload, Mapping) else ""
        summary = description.strip() if isinstance(description, str) and description.strip() else event_type
        record = WorldHistoryRecord(
            f"event:{event_id}", _timestamp(timestamp), "event_applied", event_id, summary,
            {"event_type": event_type, "actor_id": actor, "target_id": target,
             "location": getattr(event, "location", None)},
        )
        self._histories["event_history"].append(record)
        self._recorded_events.add(event_id)
        # The event notification records what was applied; it does not infer or
        # execute any state change. Explicit before/after values are preserved.
        self.record_delta(
            source=event_id, target=str(target), change_type=event_type,
            before=payload.get("before") if isinstance(payload, Mapping) else None,
            after=payload.get("after", payload) if isinstance(payload, Mapping) else None,
            cause=summary, timestamp=timestamp, record_id=f"event-delta:{event_id}",
        )
        return record

    def handle_event(self, event, context=None):
        return self.record_event(event, context)

    def record_opportunity(self, opportunity_id, action, *, timestamp=None, cause="", metadata=None):
        return self._record_lifecycle("opportunity_history", "opportunity", opportunity_id,
                                      action, timestamp, cause, metadata)

    def record_conflict(self, conflict_id, action, *, before=None, after=None,
                        timestamp=None, cause="", metadata=None):
        self.record_delta(source=str(conflict_id), target=str(conflict_id),
                          change_type=f"conflict_{action}", before=before, after=after,
                          cause=cause or action, timestamp=timestamp)
        return self._record_lifecycle("conflict_history", "conflict", conflict_id,
                                      action, timestamp, cause, metadata)

    def record_decision(self, actor_id, decision, *, timestamp=None, reason_context="",
                        target=None, metadata=None):
        details = dict(metadata or {})
        details.update({"actor_id": str(actor_id), "decision": str(decision),
                        "target": target, "reason_context": reason_context})
        return self._record_lifecycle("decision_history", "decision", str(actor_id),
                                      str(decision), timestamp, reason_context or str(decision), details)

    def record_relationship(self, source_id, target_id, *, before=None, after=None,
                            timestamp=None, cause=""):
        record = self._record_lifecycle(
            "relationship_history", "relationship", f"{source_id}->{target_id}",
            "changed", timestamp, cause or "relationship state changed",
            {"source_id": str(source_id), "target_id": str(target_id),
             "before": before, "after": after},
        )
        self.record_delta(source=f"{source_id}->{target_id}", target=str(target_id),
                          change_type="relationship_changed", before=before, after=after,
                          cause=cause or "relationship state changed", timestamp=timestamp)
        return record

    def record_world_tree(self, action, branch_id, *, timestamp=None, cause="", metadata=None):
        return self._record_lifecycle("world_tree_history", "world_tree", branch_id,
                                      action, timestamp, cause or action, metadata)

    def _record_lifecycle(self, bucket, record_type, source_id, action, timestamp, cause, metadata):
        source_id = str(source_id)
        action = str(action)
        record = WorldHistoryRecord(
            f"{record_type}:{source_id}:{action}:{uuid4().hex}", _timestamp(timestamp),
            f"{record_type}_{action}", source_id, str(cause or action),
            {"action": action, **dict(metadata or {})},
        )
        self._histories[bucket].append(record)
        return record


__all__ = ["WorldDelta", "WorldHistoryRecord", "WorldHistory", "WorldMemorySnapshot", "WorldMemory"]
