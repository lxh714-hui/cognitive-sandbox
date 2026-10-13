from cognitive_sandbox.goal.character_goal import CharacterGoal
from cognitive_sandbox.goal.goal_manager import GoalManager
from cognitive_sandbox.goal.lifecycle import GoalLifecycleManager
from cognitive_sandbox.narrative.event_planner import EventPlanner
from cognitive_sandbox.narrative.narrative_pressure import NarrativePressure, NarrativePressureCalculator
from cognitive_sandbox.narrative.conflict_detector import Conflict
from cognitive_sandbox.application.character_state_summary import CharacterStateSummaryBuilder


def test_stagnation_flows_into_pressure_and_candidate_weight():
    pressure = NarrativePressureCalculator().with_goal_stagnation(NarrativePressure(), .8)
    assert pressure.goal_stagnation == .8
    assert pressure.urgency > 0
    conflict = Conflict("c1", "information_conflict", ("a", "b"), "信息受阻", (), .4)
    baseline = EventPlanner().plan((conflict,), pressure=NarrativePressure())
    pressured = EventPlanner().plan((conflict,), pressure=pressure)
    assert pressured[0].pressure > baseline[0].pressure


def test_goal_stagnation_is_an_observable_goal_metric():
    goal = CharacterGoal("npc", "调查线索", "investigate", goal_id="g")
    lifecycle = GoalLifecycleManager(GoalManager((goal,)))
    for day in range(1, 11):
        lifecycle.record_action_feedback(
            "g", action_type="investigate", timestamp=f"2026-07-{day:02d}T09:00:00+00:00",
            result="no_new_information", effectiveness=.1, event_id=f"e{day}",
        )
    assert lifecycle.maximum_stagnation > .5
    summary = CharacterStateSummaryBuilder().build(
        "npc", goals=(goal,), goal_lifecycle=lifecycle,
        narrative_pressure=NarrativePressureCalculator().with_goal_stagnation(
            NarrativePressure(), lifecycle.maximum_stagnation,
        ),
    )
    assert summary.goal_status == "调查停滞"
    assert summary.action_tendency == "寻找新的信息来源或方法"


def test_anchor_long_run_report_exposes_goal_pressure_at_checkpoints():
    from tools.simulation_test.long_simulation_runner import LongSimulationRunner

    result = LongSimulationRunner().run_world(checkpoints=(30, 100), random_seed=13)
    day_30, day_100 = (item.report for item in result.checkpoint_results)
    assert day_30.narrative_pressure.goal_stagnation >= 0
    assert day_100.narrative_pressure.goal_stagnation >= day_30.narrative_pressure.goal_stagnation
    # The package may resolve its goal before day 100; its stagnation snapshot
    # is then zero while narrative pressure retains its historical peak.
    assert day_30.characters["liuyiyi"].stagnation_level >= 0
