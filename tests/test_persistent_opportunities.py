from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.narrative.opportunity import (
    NarrativeOpportunity, OpportunityManager, OpportunitySourceType,
)
from cognitive_sandbox.persistence.models.save_metadata import SaveMetadata
from cognitive_sandbox.persistence.world_serializer import WorldSerializer


def test_creating_opportunity_does_not_change_world_or_create_world_event():
    session = GameLauncher().start_world("anchor")
    world_before = dict(session.world_state)
    events_before = tuple(session.executor.event_timeline.events)
    opportunity = next(item for item in session.opportunity_service.snapshot()
                       if item.opportunity_id == "investigate_clock")

    assert opportunity.description.startswith("墙上的钟停在12:03")
    assert opportunity.candidate_actions[0].intent == "inspect"
    assert dict(session.world_state) == world_before
    assert tuple(session.executor.event_timeline.events) == events_before


def test_opportunity_is_immutable_and_internal_context_is_deeply_read_only():
    context = {"source": {"location": "home"}}
    opportunity = NarrativeOpportunity(
        "op-test", OpportunitySourceType.WORLD, description="可能值得查看。",
        internal_context=context,
    )
    context["source"]["location"] = "changed"
    assert opportunity.internal_context["source"]["location"] == "home"
    with pytest.raises(TypeError):
        opportunity.internal_context["source"]["location"] = "changed"
    with pytest.raises(FrozenInstanceError):
        opportunity.description = "已发生"


def test_opportunities_and_world_tree_round_trip_in_world_save():
    session = GameLauncher().start_world("anchor")
    metadata = SaveMetadata(
        session.world_instance_id, session.executor.world_id, "anchor", "锚点",
        "世界简介", session.scenario_started_at,
        session.executor.world_clock.current_time().isoformat(),
        player_character_id=session.player_id,
    )
    serializer = WorldSerializer()
    decoded = serializer.deserialize_world(serializer.serialize_world(metadata, session))
    narrative = decoded["narrative"]

    assert any(item.opportunity_id == "investigate_clock" for item in narrative["opportunities"])
    assert narrative["world_tree"]["branches"]
    restored = GameLauncher().restore_saved_world(decoded)
    active = restored.opportunity_service.for_character(restored.player_id)
    assert any(item.opportunity_id == "investigate_clock" for item in active)
    assert restored.executor.world_tree_manager.snapshot()["branches"] == narrative["world_tree"]["branches"]


def test_old_saves_default_to_empty_opportunity_and_tree_state():
    session = GameLauncher().start_world("anchor")
    metadata = SaveMetadata(
        session.world_instance_id, session.executor.world_id, "anchor", "锚点",
        "世界简介", session.scenario_started_at,
        session.executor.world_clock.current_time().isoformat(),
        player_character_id=session.player_id,
    )
    payload = WorldSerializer().serialize_world(metadata, session)
    payload["narrative"]["$mapping"] = [
        pair for pair in payload["narrative"]["$mapping"]
        if pair[0] not in {"opportunities", "world_tree"}
    ]
    payload.pop("opportunities")
    payload.pop("world_tree")
    decoded = WorldSerializer().deserialize_world(payload)
    assert decoded["narrative"]["opportunities"] == ()
    assert decoded["narrative"]["world_tree"] == {}


def test_opportunity_manager_restores_unresolved_records_and_resolves_after_selection():
    manager = OpportunityManager()
    action = ActionCandidate("inspect", actor_id="player", intent="inspect", target="钟")
    item = manager.register(NarrativeOpportunity(
        "clock", OpportunitySourceType.WORLD, visibility="public", description="钟停住了。",
        candidate_actions=(action,),
    ))
    restored = OpportunityManager()
    restored.restore(manager.snapshot())
    assert restored.visible_to("player")[0] == item
    assert restored.resolve("clock").status.value == "resolved"
    assert restored.visible_to("player") == ()
