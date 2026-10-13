from cognitive_sandbox.application.game_launcher import GameLauncher


def test_anchor_runtime_exposes_scoped_opportunities_without_changing_world_or_creating_events():
    session = GameLauncher().start_anchor_world()
    before_state = dict(session.world_state)
    before_events = tuple(session.executor.event_timeline.events)
    service = session.opportunity_service
    assert service is not None
    liuyiyi = service.for_character("liuyiyi")
    assert isinstance(liuyiyi, tuple)
    assert all(item.is_visible_to("liuyiyi") for item in liuyiyi)
    liang = service.for_character("liangjing")
    assert all(item.is_visible_to("liangjing") for item in liang)
    assert dict(session.world_state) == before_state
    assert tuple(session.executor.event_timeline.events) == before_events


def test_player_may_ignore_all_opportunities_without_simulation_effect():
    session = GameLauncher().start_anchor_world()
    world_before = dict(session.world_state)
    event_count = len(session.executor.event_timeline.events)
    _visible = session.opportunity_service.for_character(session.player_id)
    assert dict(session.world_state) == world_before
    assert len(session.executor.event_timeline.events) == event_count
