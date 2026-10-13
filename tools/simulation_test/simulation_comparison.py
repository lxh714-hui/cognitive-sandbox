from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationComparison:
    left_day: int
    right_day: int
    event_delta: int
    activity_delta: float
    relationship_delta: int
    information_flow_delta: int
    narrative_delta: int


class SimulationComparator:
    def compare(self, left, right, left_day, right_day, *, left_emergence=None, right_emergence=None):
        left_report = getattr(left, "report", left)
        right_report = getattr(right, "report", right)
        left_emergence = left_emergence or getattr(left, "emergence_report", None)
        right_emergence = right_emergence or getattr(right, "emergence_report", None)
        left_events = getattr(left, "cumulative_event_count", len(left_report.events))
        right_events = getattr(right, "cumulative_event_count", len(right_report.events))
        left_relationships = getattr(left, "relationship_transition_count", len(left_report.relationship_transitions))
        right_relationships = getattr(right, "relationship_transition_count", len(right_report.relationship_transitions))
        left_flow = getattr(left_emergence, "information_flow", 0)
        right_flow = getattr(right_emergence, "information_flow", 0)
        left_narrative = getattr(left_emergence, "narrative_development", len(left_report.thread_changes))
        right_narrative = getattr(right_emergence, "narrative_development", len(right_report.thread_changes))
        return SimulationComparison(
            left_day, right_day, right_events - left_events,
            right_report.metrics.character_independence - left_report.metrics.character_independence,
            right_relationships - left_relationships,
            right_flow - left_flow,
            right_narrative - left_narrative,
        )
