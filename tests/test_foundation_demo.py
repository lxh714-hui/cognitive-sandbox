from examples.basic_simulation_demo import run_demo


def test_demo_runs_and_prints_results(capsys):
    demo = run_demo()

    output = capsys.readouterr().out
    assert "原始世界状态" in output
    assert "生成事件" in output
    assert "新世界状态" in output
    assert demo["result"].events


def test_demo_tick_generates_expected_event():
    result = run_demo()["result"]

    assert len(result.events) == 1
    assert result.events[0].event_type == "help_attempt"
    assert result.events[0].actor_id == "doctor-1"


def test_demo_tick_changes_world_state():
    demo = run_demo()
    result = demo["result"]

    assert demo["initial_world_state"]["social_trust"] == 0.5
    assert result.world_state["social_trust"] == 0.6


def test_demo_tick_appends_experience_memory():
    demo = run_demo()

    assert len(demo["result"].agent_context.memories) == len(demo["initial_context"].memories) + 1
    assert demo["result"].agent_context.memories[-1].content == "我曾经帮助过他人"


def test_demo_tick_updates_relationship_and_dynamic_state():
    demo = run_demo()
    before = demo["initial_context"]
    after = demo["result"].agent_context

    assert after.relationships[0].trust == 0.7
    assert after.dynamic_state.confidence == 0.55
    assert after.dynamic_state.motivation == 0.65
    assert after.dynamic_state != before.dynamic_state
