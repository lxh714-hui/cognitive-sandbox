from __future__ import annotations

from datetime import datetime

from .encounter_candidate import EncounterCandidate, EncounterStatus, EncounterTrajectory
from .encounter_condition import LocationCondition, TimeCondition


class EncounterGenerator:
    """Builds a possibility from two observed, co-located action trajectories."""

    def generate(self, first: EncounterTrajectory, second: EncounterTrajectory, *,
                 location: str | None = None, reason: str = "行动轨迹在同一地点重合") -> EncounterCandidate:
        if not isinstance(first, EncounterTrajectory) or not isinstance(second, EncounterTrajectory):
            raise TypeError("encounter generation requires two EncounterTrajectory values.")
        if first.character_id == second.character_id:
            raise ValueError("an encounter requires two distinct characters.")
        matched_location = _normalize(first.location) == _normalize(second.location)
        matched_time = _within_window(first.timestamp, second.timestamp)
        first_time, second_time = sorted((first.timestamp, second.timestamp))
        when = f"{first_time}/{second_time}"
        candidate = EncounterCandidate(
            first.character_id, second.character_id, location or first.location,
            when, reason, 0.0,
            (LocationCondition(first.location, second.location, matched_location,
                               "地点一致" if matched_location else "地点不同"),
             TimeCondition(first.timestamp, second.timestamp, matched_time,
                           "行动时间接近" if matched_time else "行动时间不重叠")),
            EncounterStatus.POSSIBLE,
            source_event_ids=(first.source_event_id, second.source_event_id),
            activity_a=first.public_activity or first.action_type,
            activity_b=second.public_activity or second.action_type,
        )
        # Stable per pair/location/time-window identity prevents duplicate encounters
        # when the same event is delivered to more than one listener.
        bucket = _bucket(first.timestamp if first.timestamp >= second.timestamp else second.timestamp)
        pair = ":".join(sorted((first.character_id, second.character_id)))
        stable = f"enc:{pair}:{_normalize(candidate.location)}:{bucket}"
        return EncounterCandidate(
            candidate.character_a, candidate.character_b, candidate.location, candidate.time_window,
            candidate.reason, candidate.score, candidate.conditions, candidate.status, stable,
            candidate.willingness_a, candidate.willingness_b, candidate.source_event_ids,
            candidate.activity_a, candidate.activity_b,
        )


def _normalize(value):
    return " ".join(str(value).strip().casefold().split())


def _parse(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _within_window(first, second, hours=8):
    a, b = _parse(first), _parse(second)
    if a is None or b is None:
        return first == second
    try:
        return abs((a - b).total_seconds()) <= hours * 3600
    except TypeError:
        return False


def _bucket(value):
    parsed = _parse(value)
    if parsed is None:
        return str(value)
    return parsed.replace(minute=0, second=0, microsecond=0).isoformat()


__all__ = ["EncounterGenerator"]
