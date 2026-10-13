from types import SimpleNamespace

from cognitive_sandbox.presentation.debug.narrative_replay import filter_story_events


def test_story_view_hides_routine_events_by_default_but_can_show_details():
    routine = SimpleNamespace(event_type="npc_worked", metadata={"importance_level": 0})
    key = SimpleNamespace(event_type="npc_investigated", metadata={"importance_level": 2})
    assert filter_story_events((routine, key)) == (key,)
    assert filter_story_events((routine, key), include_routine=True) == (routine, key)
