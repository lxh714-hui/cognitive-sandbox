from datetime import datetime, timezone

from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.goal.character_goal import CharacterGoal
from cognitive_sandbox.goal.goal_manager import GoalManager
from cognitive_sandbox.npc.autonomous.npc_action_executor import NpcActionExecutor
from cognitive_sandbox.npc.autonomous.npc_action_generator import NpcActionGenerator
from cognitive_sandbox.npc.autonomous.npc_scheduler import NpcScheduler
from cognitive_sandbox.time.world_clock import WorldClock


def test_guard_patrol_and_doctor_collect_materials_on_world_tick():
    clock = WorldClock("2030-01-01T20:00:00+00:00")
    goals = GoalManager((
        CharacterGoal("guard", "巡逻区域", "protect_city", .8, ("patrol_time",)),
        CharacterGoal("doctor", "修复医疗站", "repair_clinic", .7, ("materials_needed",)),
    ))
    scheduler = NpcScheduler(
        {"guard": object(), "doctor": object()}, goals, clock=clock,
        action_generator=NpcActionGenerator((
            {"goal_type": "repair_clinic", "action_type": "collect", "reason": "configured collection"},
            {"goal_type": "protect_city", "action_type": "patrol", "reason": "configured patrol"},
        )),
        action_executor=NpcActionExecutor(
            world_id="w", id_factory=iter(("1", "2")).__next__,
            event_types={"collect": "npc_materials_collected", "patrol": "npc_patrolled"},
        ),
        goal_evaluator=__import__("cognitive_sandbox.goal.goal_evaluator", fromlist=["GoalEvaluator"]).GoalEvaluator({
            "patrol_time": {"type": "time_window", "start_hour": 18, "end_hour": 6},
            "materials_needed": True,
        }),
    )
    tick = WorldEvent("tick-1", "main", "w", "world_tick", "system", {}, 1, timestamp=clock.current_time().isoformat())
    context = type("Context", (), {"world_clock": clock, "world_state": {"location": "north"}})()

    events = scheduler.handle_event(tick, context)

    assert [event.event_type for event in events] == ["npc_materials_collected", "npc_patrolled"]
    assert [event.actor_id for event in events] == ["doctor", "guard"]
    assert scheduler.handle_event(tick, context) == ()


def test_unsupported_npc_action_does_not_create_world_event():
    from cognitive_sandbox.application.npc.npc_action import NpcAction
    executor = NpcActionExecutor()
    assert executor.execute(NpcAction("npc", "unsupported", reason="no registered rule")) is None
