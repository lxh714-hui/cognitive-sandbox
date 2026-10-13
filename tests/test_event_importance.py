from types import SimpleNamespace

from cognitive_sandbox.event.event_importance import event_importance_level


def test_importance_levels_distinguish_routine_progress_and_key_events():
    assert event_importance_level(SimpleNamespace(event_type="npc_worked", metadata={})) == 0
    assert event_importance_level(SimpleNamespace(event_type="npc_investigated", metadata={})) == 2
    assert event_importance_level(SimpleNamespace(event_type="custom", metadata={"importance_level": 3})) == 3
