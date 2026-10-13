from cognitive_sandbox.simulation_test.simulation_metrics import SimulationMetrics
from cognitive_sandbox.simulation_test.simulation_report import (
    CharacterSimulationSummary, NarrativeThreadSummary, SimulationReport,
)


def test_simulation_metrics_distinguish_activity_and_narrative_growth():
    metrics = SimulationMetrics.calculate(
        tick_count=4, events=(), npc_count=3, emotion_changes=2,
        knowledge_leaks=0, thread_changes=(),
    )
    assert metrics.activity_rate == 0
    assert metrics.character_independence == 0
    assert metrics.knowledge_isolation == 1
    assert metrics.emotion_dynamics > 0
    assert metrics.narrative_growth == 0


def test_report_keeps_character_and_thread_snapshots_read_only():
    character = CharacterSimulationSummary("liangjing")
    thread = NarrativeThreadSummary("t1", "调查", "DORMANT", 0, .2, ("liuyiyi",))
    report = SimulationReport(
        "w1", "锚点", 0, "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00",
        0, (), (), {"liangjing": character}, (thread,), (), (), (),
        SimulationMetrics(0, 0, 1, 0, 0), 0, True,
    )
    try:
        report.characters["new"] = character
    except TypeError:
        pass
    else:
        raise AssertionError("report character map must be immutable")
    assert report.thread_states == (thread,)

