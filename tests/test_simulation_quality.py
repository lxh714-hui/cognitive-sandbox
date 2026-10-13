from types import SimpleNamespace

from cognitive_sandbox.simulation_test.simulation_metrics import SimulationMetrics


def event(kind, actor, action=None, importance=0):
    metadata = {"importance_level": importance}
    if action:
        metadata["action_type"] = action
    return SimpleNamespace(event_type=kind, actor_ids=(actor,), metadata=metadata)


def test_report_metrics_count_unique_repeated_conflicts_and_important_events():
    events = (event("npc_worked", "a", "work", 0), event("npc_worked", "a", "work", 0),
              event("npc_investigated", "b", "investigate", 2), event("conflict_event", "b", importance=3))
    metrics = SimulationMetrics.calculate(tick_count=4, events=events, npc_count=2, emotion_changes=0,
                                          knowledge_leaks=0, thread_changes=(),
                                          relationship_changes=(1, 2), goal_transitions=(1,))
    assert metrics.unique_actions == 2
    assert metrics.repeated_actions == 1
    assert metrics.conflict_related_events == 1
    assert metrics.relationship_changes == 2
    assert metrics.goal_transitions == 1
    assert metrics.important_events == 2
