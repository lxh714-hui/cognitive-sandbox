from __future__ import annotations

from dataclasses import dataclass

from .narrative_thread import NarrativeThread


@dataclass(frozen=True)
class NarrativeState:
    threads: tuple[NarrativeThread, ...] = ()
    candidates: tuple[object, ...] = ()
    pressure: object | None = None

    def __post_init__(self):
        for name in ("threads", "candidates"):
            values = tuple(getattr(self, name))
            if name == "threads" and any(not isinstance(value, NarrativeThread) for value in values):
                raise TypeError("threads must contain NarrativeThread values.")
            object.__setattr__(self, name, values)

    def with_thread(self, thread: NarrativeThread) -> "NarrativeState":
        if not isinstance(thread, NarrativeThread):
            raise TypeError("thread must be NarrativeThread.")
        values = {item.id: item for item in self.threads}
        values[thread.id] = thread
        return NarrativeState(tuple(values[key] for key in sorted(values)), self.candidates, self.pressure)

    def with_conflicts(self, conflicts) -> "NarrativeState":
        from cognitive_sandbox.narrative.conflict_detector import ConflictDetector

        state = self
        for thread in ConflictDetector().generate_threads(conflicts):
            state = state.with_thread(thread)
        return state

    @classmethod
    def from_snapshot(cls, *, goals=(), motivations=(), resources=(), world_state=None,
                      presence=(), locations=(), current_time=None, constraints=(), maximum_candidates=3):
        """Derive threads, pressure and candidates from a bounded runtime snapshot."""
        from dataclasses import replace
        from cognitive_sandbox.character_presence.character_presence import PresenceState
        from cognitive_sandbox.narrative.conflict_detector import ConflictDetector
        from cognitive_sandbox.narrative.event_planner import EventPlanner
        from cognitive_sandbox.narrative.narrative_pressure import NarrativePressureCalculator
        from cognitive_sandbox.narrative.narrative_thread import NarrativeThreadStatus

        detector = ConflictDetector()
        conflicts = detector.detect(goals, motivations, resources)
        by_id = {item.character_id: item for item in presence}
        threads = []
        for thread in detector.generate_threads(conflicts):
            known = [by_id[item] for item in thread.participants if item in by_id]
            visible = len(known) == len(thread.participants) and all(
                item.availability in {PresenceState.AVAILABLE, PresenceState.INTRODUCED, PresenceState.ACTIVE}
                for item in known
            )
            threads.append(replace(thread, status=NarrativeThreadStatus.ACTIVE if visible else NarrativeThreadStatus.DORMANT))
        pressure = NarrativePressureCalculator().calculate(
            conflicts,
            danger=(world_state or {}).get("danger_level", 0.0) if hasattr(world_state or {}, "get") else 0.0,
        )
        candidates = EventPlanner(detector).plan(
            conflicts,
            presence=presence,
            locations=locations,
            current_time=current_time,
            pressure=pressure,
            constraints=constraints,
            maximum=maximum_candidates,
        )
        return cls(tuple(threads), candidates, pressure)
