from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EventLifecycle(str, Enum):
    ONE_TIME = "ONE_TIME"
    REPEATABLE = "REPEATABLE"
    ONGOING = "ONGOING"


@dataclass(frozen=True)
class EventLifecyclePolicy:
    """Small deterministic lifecycle gate for candidate autonomous events."""

    def __post_init__(self):
        pass

    @staticmethod
    def can_generate(*, lifecycle, event_type, actor_id, timestamp, timeline=(), cooldown_days=0,
                     lifecycle_key=None):
        try:
            lifecycle = lifecycle if isinstance(lifecycle, EventLifecycle) else EventLifecycle(str(lifecycle).upper())
        except ValueError:
            raise ValueError("lifecycle must be ONE_TIME, REPEATABLE, or ONGOING.")
        if isinstance(cooldown_days, bool) or not isinstance(cooldown_days, int) or cooldown_days < 0:
            raise ValueError("cooldown_days must be a non-negative integer.")
        records = tuple(timeline)
        key = lifecycle_key or event_type
        matching = [item for item in records
                    if item.event_type == event_type
                    and (not actor_id or actor_id in item.actor_ids)
                    and item.metadata.get("lifecycle_key", item.event_type) == key]
        if lifecycle is EventLifecycle.ONE_TIME:
            return not matching
        if lifecycle is EventLifecycle.ONGOING:
            return not any(item.metadata.get("lifecycle_active", False) for item in matching)
        if cooldown_days == 0 or not matching:
            return True
        try:
            from datetime import datetime
            now = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            previous = datetime.fromisoformat(matching[-1].timestamp.replace("Z", "+00:00"))
            if now.tzinfo is not None and previous.tzinfo is None:
                previous = previous.replace(tzinfo=now.tzinfo)
            if now.tzinfo is None and previous.tzinfo is not None:
                now = now.replace(tzinfo=previous.tzinfo)
            return (now - previous).total_seconds() >= cooldown_days * 86400
        except (AttributeError, TypeError, ValueError):
            return False
