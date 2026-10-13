from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class WorldClockState:
    current: str

    def __post_init__(self):
        if not isinstance(self.current, str) or not self.current.strip():
            raise ValueError("current time must not be empty.")
        _parse(self.current)


class WorldClock:
    """Mutable runtime clock with an immutable save snapshot."""

    def __init__(self, current_time: datetime | str | WorldClockState | None = None):
        if isinstance(current_time, WorldClockState):
            current_time = current_time.current
        self._current = _parse(current_time) if current_time is not None else datetime.now(timezone.utc)

    def current_time(self) -> datetime:
        return self._current

    @property
    def state(self) -> WorldClockState:
        return WorldClockState(self._current.isoformat())

    def advance(self, minutes: int = 10, *, delta: timedelta | None = None) -> datetime:
        if delta is not None:
            if not isinstance(delta, timedelta) or delta.total_seconds() < 0:
                raise ValueError("delta must be a non-negative timedelta.")
            amount = delta
        else:
            if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes < 0:
                raise ValueError("minutes must be a non-negative integer.")
            amount = timedelta(minutes=minutes)
        self._current += amount
        return self._current

    def restore(self, state: WorldClockState | str) -> None:
        self._current = _parse(state.current if isinstance(state, WorldClockState) else state)


def _parse(value):
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("current time must be an ISO datetime.") from error
    else:
        raise TypeError("current time must be a datetime or ISO string.")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
