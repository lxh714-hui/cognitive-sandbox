from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from cognitive_sandbox.domain.world_events import WorldEvent


@dataclass(frozen=True)
class ScheduledWorldEvent:
    schedule_id: str
    due_time: str
    event: WorldEvent

    def __post_init__(self):
        if not self.schedule_id or not self.schedule_id.strip():
            raise ValueError("schedule_id must not be empty.")
        _parse(self.due_time)
        if not isinstance(self.event, WorldEvent):
            raise TypeError("event must be a WorldEvent.")


class TimeScheduler:
    """Store and release explicitly scheduled world events; no callbacks are persisted."""

    def __init__(self, pending=(), *, tick_count: int = 0):
        if isinstance(tick_count, bool) or not isinstance(tick_count, int) or tick_count < 0:
            raise ValueError("tick_count must be non-negative.")
        self._pending = list(pending)
        if any(not isinstance(item, ScheduledWorldEvent) for item in self._pending):
            raise TypeError("pending must contain ScheduledWorldEvent values.")
        self.tick_count = tick_count

    @property
    def pending_events(self) -> tuple[ScheduledWorldEvent, ...]:
        return tuple(sorted(self._pending, key=lambda item: (item.due_time, item.schedule_id)))

    def schedule(self, event: WorldEvent, due_time: datetime | str, *, schedule_id: str | None = None):
        from uuid import uuid4
        due = _parse(due_time).isoformat()
        entry = ScheduledWorldEvent(schedule_id or uuid4().hex, due, event)
        if any(item.schedule_id == entry.schedule_id for item in self._pending):
            raise ValueError("schedule_id must be unique.")
        self._pending.append(entry)
        return entry

    def handle_event(self, event, context=None):
        if event.event_type != "world_tick":
            return ()
        self.tick_count += 1
        clock = getattr(context, "world_clock", None)
        now = clock.current_time() if clock is not None else _parse(event.timestamp or datetime.now(timezone.utc).isoformat())
        ready = [item for item in self._pending if _parse(item.due_time) <= now]
        ready_ids = {item.schedule_id for item in ready}
        self._pending = [item for item in self._pending if item.schedule_id not in ready_ids]
        return tuple(item.event for item in sorted(ready, key=lambda item: (item.due_time, item.schedule_id)))

    def snapshot(self) -> tuple[int, tuple[ScheduledWorldEvent, ...]]:
        return self.tick_count, self.pending_events


def _parse(value):
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise TypeError("time must be a datetime or ISO string.")
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
