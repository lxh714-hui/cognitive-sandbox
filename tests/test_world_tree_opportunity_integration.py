from cognitive_sandbox.application.game_launcher import GameLauncher


def _play(session, text):
    session.submit_input(text)
    return session.confirm()


def test_world_tree_only_records_selected_opportunity_after_action_event():
    session = GameLauncher().start_world("anchor")
    service = session.opportunity_service
    tree = session.executor.world_tree_manager
    before_state = dict(session.world_state)
    before_events = tuple(session.executor.event_timeline.events)
    opportunity = next(item for item in service.for_character(session.player_id)
                       if item.opportunity_id == "investigate_clock")
    tree.register_opportunity(opportunity)

    assert dict(session.world_state) == before_state
    assert tuple(session.executor.event_timeline.events) == before_events

    leave_result = _play(session, "直接离开房间")
    assert leave_result.action_executed
    assert any(item.opportunity_id == "investigate_clock"
               for item in service.for_character(session.player_id))

    # A fresh Anchor instance chooses the clock possibility and only then gets
    # the ordinary action event from the existing action handler.
    selected_session = GameLauncher().start_world("anchor")
    result = _play(selected_session, "看看钟")
    assert result.action_executed
    assert result.simulation_result.events
    assert selected_session.executor.last_action_branch_mapping.target_opportunity == "investigate_clock"
    assert selected_session.opportunity_service.snapshot()[0].status.value == "resolved"
    assert selected_session.executor.event_timeline.events


def test_unselected_opportunity_does_not_publish_an_event():
    session = GameLauncher().start_world("anchor")
    service = session.opportunity_service
    events_before = tuple(session.executor.event_timeline.events)
    state_before = dict(session.world_state)

    service.for_character(session.player_id)

    assert tuple(session.executor.event_timeline.events) == events_before
    assert dict(session.world_state) == state_before
