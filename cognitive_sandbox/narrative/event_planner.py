from __future__ import annotations

from dataclasses import dataclass

from .conflict_detector import Conflict
from .narrative_pressure import NarrativePressure


@dataclass(frozen=True)
class CandidateEvent:
    candidate_id: str
    event_type: str
    participants: tuple[str, ...]
    location: str | None
    conditions: tuple[str, ...]
    rationale: str
    source_conflicts: tuple[str, ...]
    pressure: float

    def __post_init__(self):
        for field in ("candidate_id", "event_type", "rationale"):
            if not isinstance(getattr(self, field), str) or not getattr(self, field).strip():
                raise ValueError(f"{field} must not be empty.")
        for field in ("participants", "conditions", "source_conflicts"):
            object.__setattr__(self, field, tuple(getattr(self, field)))
        if self.location is not None and (not isinstance(self.location, str) or not self.location.strip()):
            raise ValueError("location must be None or non-empty.")
        if not 0 <= self.pressure <= 1:
            raise ValueError("pressure must be between 0 and 1.")


class EventPlanner:
    """Proposes explainable candidates; it never submits or commits WorldEvents."""

    def __init__(self, conflict_detector=None):
        from cognitive_sandbox.narrative.conflict_detector import ConflictDetector
        self.conflict_detector = conflict_detector or ConflictDetector()

    def plan_from_state(self, goals=(), motivations=(), resources=(), *, world_state=None,
                        presence=(), locations=(), current_time=None, pressure=None, anchors=(), maximum=3):
        """Build candidates from a current snapshot and explicit conflict sources."""
        conflicts = self.conflict_detector.detect(goals, motivations, resources)
        if pressure is None and isinstance(world_state, dict):
            raw_danger = world_state.get("danger_level", 0.0)
            danger = float(raw_danger) if isinstance(raw_danger, (int, float)) and not isinstance(raw_danger, bool) else 0.0
            from cognitive_sandbox.narrative.narrative_pressure import NarrativePressureCalculator
            pressure = NarrativePressureCalculator().calculate(conflicts, danger=danger)
        return self.plan(conflicts, presence=presence, locations=locations, current_time=current_time,
                         pressure=pressure, anchors=anchors, maximum=maximum)

    def plan(self, conflicts=(), *, presence=(), locations=(), current_time=None,
             pressure: NarrativePressure | None = None, anchors=(), maximum=3):
        conflicts = tuple(conflicts)
        presences = {item.character_id: item for item in presence}
        location_ids = {getattr(item, "location_id", None) or getattr(item, "id", None) for item in locations}
        result = []
        for conflict in conflicts:
            if not isinstance(conflict, Conflict):
                continue
            participants = tuple(
                identity for identity in conflict.participants
                if identity not in presences or getattr(presences[identity].availability, "value", presences[identity].availability)
                in {"INTRODUCED", "ACTIVE", "AVAILABLE"}
            )
            if not participants:
                continue
            location = next((presences[item].current_location for item in participants
                             if item in presences and presences[item].current_location), None)
            if location and location_ids and location not in location_ids:
                # Keep the candidate conditional; do not teleport a character or invalidate the world snapshot.
                condition = (f"location_available:{location}",)
            else:
                condition = ("conflict_remains_unresolved",)
            participant_locations = {
                presences[item].current_location for item in participants
                if item in presences and presences[item].current_location
            }
            if len(participant_locations) > 1 and location:
                condition += (f"participants_must_travel_to:{location}",)
            if current_time:
                condition += (f"after:{current_time}",)
            event_type = {
                "information_conflict": "information_lead_emerges",
                "resource_conflict": "resource_opportunity",
                "value_conflict": "dilemma_presents_itself",
                "internal_conflict": "goal_pressure_increases",
            }.get(conflict.conflict_type, "conflict_develops")
            event = CandidateEvent(
                f"candidate:{conflict.conflict_id}", event_type, participants, location, condition,
                f"候选由冲突产生：{conflict.description}", (conflict.conflict_id,),
                min(1.0, conflict.pressure + (pressure.urgency * 0.15 if pressure else 0.0)
                    + (pressure.goal_stagnation * 0.2 if pressure else 0.0)
                    + (pressure.conflict_pressure * 0.2 if pressure else 0.0)),
            )
            result.append(event)
        # Anchor objectives can shape candidates, but only if causal conditions are represented.
        for anchor in anchors:
            target = getattr(anchor, "target", None)
            if target in presences and getattr(presences[target].availability, "value", None) in {"UNKNOWN", "LEFT"}:
                continue
            result.append(CandidateEvent(
                f"candidate:anchor:{target}:{len(result)}", "objective_opportunity",
                (target,) if target else (), None, ("world_conditions_must_allow", "no_teleportation"),
                f"导演约束作为软目标等待因果条件：{anchor.objective}", (),
                min(1.0, max(0.0, getattr(anchor, "priority", 0) / 10)),
            ))
        result.sort(key=lambda item: (-item.pressure, item.candidate_id))
        return tuple(result[:max(0, int(maximum))])
