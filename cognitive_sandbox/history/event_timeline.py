from __future__ import annotations

from datetime import datetime, timezone
import re
from threading import RLock

from cognitive_sandbox.history.event_query import EventQuery
from cognitive_sandbox.history.world_event_record import WorldEventRecord


class EventTimeline:
    """Append-only, time-sorted history for one runtime world."""

    def __init__(self, records=(), *, clock=None):
        self._clock = clock or (lambda: datetime.now(timezone.utc).isoformat())
        self._records: dict[str, WorldEventRecord] = {}
        self._lock = RLock()
        self.restore(records)

    @property
    def events(self) -> tuple[WorldEventRecord, ...]:
        with self._lock:
            # Python's stable sort preserves append order for multiple events
            # recorded at the same simulation timestamp.
            return tuple(sorted(self._records.values(), key=lambda item: _time_key(item.timestamp)))

    def contains(self, event_id: str) -> bool:
        with self._lock:
            return event_id in self._records

    def record_event(self, event) -> WorldEventRecord:
        event_id = getattr(event, "event_id", None)
        with self._lock:
            existing = self._records.get(event_id)
        fallback_time = existing.timestamp if existing is not None else self._clock()
        record = event if isinstance(event, WorldEventRecord) else WorldEventRecord.from_world_event(event, timestamp=fallback_time)
        with self._lock:
            existing = self._records.get(record.event_id)
            if existing is not None:
                if existing != record:
                    raise ValueError(f"event id already recorded with different data: {record.event_id}")
                return existing
            self._records[record.event_id] = record
        return record

    def get_recent_events(self, limit: int = 20) -> tuple[WorldEventRecord, ...]:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
            raise ValueError("limit must be a non-negative integer.")
        return tuple(reversed(self.events[-limit:])) if limit else ()

    def query_events(self, query: EventQuery | None = None, **filters) -> tuple[WorldEventRecord, ...]:
        if query is not None and filters:
            raise ValueError("provide either an EventQuery or keyword filters, not both.")
        query = query or EventQuery(**filters)
        if not isinstance(query, EventQuery):
            raise TypeError("query must be an EventQuery.")
        return tuple(record for record in self.events if query.matches(record))

    def restore(self, records) -> None:
        values = tuple(records)
        if any(not isinstance(item, WorldEventRecord) for item in values):
            raise TypeError("timeline records must be WorldEventRecord values.")
        if len({item.event_id for item in values}) != len(values):
            raise ValueError("timeline contains duplicate event IDs.")
        with self._lock:
            self._records = {item.event_id: item for item in values}


def _time_key(value: str):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return (0, parsed.timestamp(), value)
    except ValueError:
        match = re.search(r"(\d+)", value)
        if match:
            prefix = value[:match.start()].casefold()
            return (1, prefix, int(match.group(1)), value)
        return (2, value.casefold(), value)
