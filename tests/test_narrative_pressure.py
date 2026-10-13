from cognitive_sandbox.agency.narrative_activity_tracker import AgencyNarrativeTracker
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.narrative.narrative_state import NarrativeState
from cognitive_sandbox.narrative.narrative_thread import NarrativeThread


def test_repeated_goal_actions_raise_thread_pressure_and_offer_candidate():
    state = NarrativeState(threads=(NarrativeThread(
        "anomaly", "异常调查", ("liuyiyi", "song"), "寻找异常线索",
    ),))
    tracker = AgencyNarrativeTracker()
    for index in range(5):
        event = WorldEvent(f"e{index}", "main", "w", "npc_investigated", "liuyiyi",
                           {"description": "核实已知线索"}, index, location="neighborhood")
        state = tracker.apply(state, event)
    thread = state.threads[0]
    assert thread.progress == .2
    assert thread.pressure == .3
    assert any(item.event_type == "thread_pressure_opportunity" for item in state.candidates)
    assert not any(item.event_type == "npc_investigated" for item in state.candidates)
