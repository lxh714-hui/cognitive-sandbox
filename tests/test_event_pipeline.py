from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.event.event_bus import EventBus
from cognitive_sandbox.event.event_pipeline import EventPipeline


def _event():
    return WorldEvent("ev-1", "main", "w", "test_event", "player", {}, 0)


def test_publish_notifies_multiple_listeners_in_stable_registration_order():
    seen = []
    pipeline = EventPipeline()
    pipeline.subscribe(lambda event, _ctx: seen.append(("first", event.event_id)), name="first")
    pipeline.subscribe(lambda event, _ctx: seen.append(("second", event.event_id)), name="second")

    published = pipeline.publish(_event())

    assert [name for name, _ in seen] == ["first", "second"]
    assert published == (_event(),)


def test_listener_exception_does_not_block_later_listeners():
    bus = EventBus()
    seen = []
    bus.subscribe(lambda *_: (_ for _ in ()).throw(RuntimeError("boom")), name="broken")
    bus.subscribe(lambda event, _ctx: seen.append(event.event_id), name="healthy")

    bus.publish(_event())

    assert seen == ["ev-1"]
    assert bus.errors[0].listener_name == "broken"


def test_world_depth_listeners_are_registered_in_evolution_to_scheduler_order():
    pipeline = EventPipeline(
        world_evolution_engine=lambda *_: None,
        event_timeline=lambda *_: None,
        knowledge_handler=lambda *_: None,
        relationship_manager=lambda *_: None,
        npc_response_service=lambda *_: None,
        autonomous_scheduler=lambda *_: None,
        scheduler=lambda *_: None,
    )

    assert [listener.name for listener in pipeline.bus.listeners] == [
        "world_evolution", "history", "knowledge", "relationship",
        "npc_response", "autonomous_npc", "scheduler",
    ]
