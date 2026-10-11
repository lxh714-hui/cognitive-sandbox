from cognitive_sandbox.application.cognitive_runtime import CognitiveRuntime
from cognitive_sandbox.application.decision_runtime import DecisionRuntime
from cognitive_sandbox.application.observation_layer import ObservationRuntime
from cognitive_sandbox.application.world_runtime import WorldRuntime
from cognitive_sandbox.domain.actions import ActionProposal
from cognitive_sandbox.domain.models import Agent
from cognitive_sandbox.domain.observations import PerceptionContext, VisibleObjectFacts
from cognitive_sandbox.infrastructure.sqlite_store import SQLiteEventStore


def make_world(store):
    runtime = WorldRuntime(
        store,
        world_id="harbor",
        branch_id="main",
        breakable_object_ids={"cup_001"},
    )
    event = runtime.submit_action(
        ActionProposal(
            proposal_id="break-cup",
            actor_id="liang-jing",
            action_type="BREAK_OBJECT",
            target_id="cup_001",
            payload={"location_id": "kitchen"},
            branch_id="main",
            world_id="harbor",
            base_world_revision=0,
        )
    )
    return runtime, event


def agent(agent_id):
    return Agent(
        id=agent_id,
        world_id="harbor",
        name=agent_id,
        role="resident",
        persona="observant",
        sprite_key=agent_id,
    )


def context(*, location="kitchen", event_location="kitchen", can_see=True, can_hear=True):
    return PerceptionContext(
        agent_location_id=location,
        event_location_id=event_location,
        can_see=can_see,
        can_hear=can_hear,
    )


def test_agent_outside_event_location_gets_no_observation(tmp_path):
    store = SQLiteEventStore(tmp_path / "feedback.sqlite3")
    _, event = make_world(store)
    runtime = ObservationRuntime(store)

    result = runtime.generate_observation(
        agent("lin-xia"), event, context=context(location="bedroom")
    )

    assert result == []


def test_blocked_visual_channel_falls_back_to_auditory_perception(tmp_path):
    store = SQLiteEventStore(tmp_path / "feedback.sqlite3")
    _, event = make_world(store)
    runtime = ObservationRuntime(store)

    [result] = runtime.generate_observation(
        agent("lin-xia"),
        event,
        context=context(can_see=False, can_hear=True),
    )

    assert result.channel == "auditory"
    assert result.content == "听到物体破碎的声音。"
    assert "liang-jing" not in result.content


def test_inspection_exposes_only_whitelisted_visible_facts(tmp_path):
    store = SQLiteEventStore(tmp_path / "feedback.sqlite3")
    world, _ = make_world(store)
    inspected_event = world.submit_action(
        ActionProposal(
            proposal_id="lin-inspects-cup",
            actor_id="lin-xia",
            action_type="INSPECT_OBJECT",
            target_id="cup_001",
            payload={"object_id": "cup_001"},
            branch_id="main",
            world_id="harbor",
            base_world_revision=1,
        )
    )
    runtime = ObservationRuntime(store)

    [result] = runtime.generate_observation(
        agent("lin-xia"),
        inspected_event,
        context=context(),
        visible_object_facts=VisibleObjectFacts(
            object_id="cup_001",
            is_broken=True,
            material_visible="glass",
            crack_pattern_visible="radial",
        ),
    )

    assert "玻璃碎片散落在地面" in result.content
    assert "裂纹呈radial" in result.content
    assert "liang-jing" not in result.content
    assert "accident" not in result.content
    assert result.event_ref == inspected_event.event_id
    assert result.source_refs == (inspected_event.event_id,)


def test_actor_and_bystander_receive_different_observation_records(tmp_path):
    store = SQLiteEventStore(tmp_path / "feedback.sqlite3")
    _, event = make_world(store)
    runtime = ObservationRuntime(store)

    [actor_result] = runtime.generate_observation(
        agent("liang-jing"), event, context=context(can_see=False, can_hear=False)
    )
    [bystander_result] = runtime.generate_observation(
        agent("lin-xia"), event, context=context()
    )

    assert actor_result.channel == "action"
    assert actor_result.content == "我打碎了物体 cup_001。"
    assert bystander_result.channel == "visual"
    assert bystander_result.content == "看到物体 cup_001 碎裂，碎片散落。"
    assert actor_result.event_ref == bystander_result.event_ref == event.event_id


def test_inspection_feedback_enters_working_memory_with_source_chain(tmp_path):
    store = SQLiteEventStore(tmp_path / "feedback.sqlite3")
    world, break_event = make_world(store)
    observations = ObservationRuntime(store)
    cognition = CognitiveRuntime(store)

    [first_observation] = observations.generate_observation(
        agent("lin-xia"), break_event, context=context()
    )
    cognition.process_observation(first_observation)
    [proposal] = DecisionRuntime(cognition).generate_actions("lin-xia")
    inspect_event = world.submit_action(proposal)
    [inspection_result] = observations.generate_observation(
        agent("lin-xia"),
        inspect_event,
        context=context(),
        visible_object_facts=VisibleObjectFacts("cup_001", is_broken=True, material_visible="glass"),
    )
    state = cognition.process_observation(inspection_result)

    assert state.cognitive_revision == 2
    assert len(state.working_memory) == 2
    assert state.working_memory[-1].content["text"] == inspection_result.content
    assert state.working_memory[-1].source_refs == (inspection_result.observation_id,)
    assert inspection_result.source_refs == (inspect_event.event_id,)
    assert [event.event_type for event in store.list_world_events("harbor")] == [
        "BREAK_OBJECT",
        "OBJECT_INSPECTED",
    ]
