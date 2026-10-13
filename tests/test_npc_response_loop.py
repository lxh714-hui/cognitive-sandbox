from types import SimpleNamespace

import pytest

from cognitive_sandbox.application.npc import NpcAction, NpcDecisionEngine, NpcEventFilter, NpcResponseService
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.domain.character_mind import CharacterMind, Identity, KnowledgeContext, PersonalityProfile
from cognitive_sandbox.domain.relationship import RelationshipState
from cognitive_sandbox.domain.world_events import WorldEvent


def _agent(character_id, name, role, location="market"):
    return AgentContext(
        character_id=character_id,
        character_state=CharacterState(character_id, name, role, (), (), (), ()),
        memories=(), relationships=(), world_state={"location": location},
    )


def _mind(role, owner_id, records=()):
    return CharacterMind(
        identity=Identity("士兵" if role == "soldier" else "商人", role),
        personality=PersonalityProfile(traits=("警觉",) if role == "soldier" else ()),
        knowledge_context=KnowledgeContext(records=tuple(records), owner_id=owner_id),
    )


def _event(**kwargs):
    values = dict(
        event_id="e1", branch_id="main", world_id="w1", event_type="weapon_drawn",
        actor_id="player", payload={"weapon": "knife"}, world_revision=4,
        location="market", timestamp="2026-10-12T12:00:00+00:00", metadata={"visible_to": ("soldier", "merchant")},
    )
    values.update(kwargs)
    return WorldEvent(**values)


def test_world_event_keeps_old_constructor_and_exposes_new_event_fields():
    old = WorldEvent("old", "main", "w1", "help_attempt", "player", {}, 2)
    assert old.actor == "player"
    assert old.target is None
    assert old.timestamp is None
    assert old.metadata is None

    event = _event(target_id="guard", metadata={"source": "visible"})
    assert event.target == "guard"
    with pytest.raises(TypeError):
        event.metadata["source"] = "changed"

    named = WorldEvent(
        event_id="named", event_type="weapon_drawn", actor="player", target="soldier",
        location="market", timestamp="t", metadata={"visible_to": ["soldier"]},
    )
    assert named.actor_id == "player" and named.target_id == "soldier"
    assert named.metadata["visible_to"] == ("soldier",)


def test_event_filter_uses_location_visibility_and_relevance():
    soldier = _agent("soldier", "林队长", "soldier")
    merchant_far = _agent("merchant", "商人", "merchant", "docks")
    doctor = _agent("doctor", "医生", "doctor")
    event = _event()
    filtered = NpcEventFilter().filter(event, (soldier, merchant_far, doctor))
    assert filtered == (soldier,)


def test_event_filter_allows_only_explicitly_visible_npcs():
    soldier = _agent("soldier", "林队长", "soldier")
    merchant = _agent("merchant", "商人", "merchant")
    event = _event(metadata={"visible_to": ("merchant",)})
    assert NpcEventFilter().filter(event, (soldier, merchant)) == ()


def test_event_filter_allows_remote_npc_only_when_its_knowledge_context_has_event():
    remote_soldier = _agent("soldier", "林队长", "soldier", "docks")
    mind = _mind("soldier", "soldier")
    mind = CharacterMind(
        mind.identity, mind.personality,
        knowledge_context=KnowledgeContext(available_information=("e1: weapon drawn",), owner_id="soldier"),
    )
    event = _event(metadata={"observable": False})
    assert NpcEventFilter().filter(
        event, (remote_soldier,), character_minds={"soldier": mind}
    ) == (remote_soldier,)


def test_npc_decision_engine_returns_structured_candidates_without_world_mutation():
    soldier = _agent("soldier", "林队长", "soldier")
    mind = _mind("soldier", "soldier")
    event = _event()
    before = dict(soldier.world_state)
    actions = NpcDecisionEngine().decide(mind, mind.knowledge_context, event, npc_context=soldier)
    assert [action.action_type for action in actions] == ["warn", "approach", "ignore"]
    assert all(action.actor_id == "soldier" and action.target == "player" for action in actions)
    assert dict(soldier.world_state) == before
    with pytest.raises(TypeError):
        actions[0].parameters["x"] = 1


def test_npc_decision_uses_directional_trust_when_ordering_candidates():
    soldier = _agent("soldier", "林队长", "soldier")
    mind = _mind("soldier", "soldier")
    actions = NpcDecisionEngine().decide(
        mind, mind.knowledge_context, _event(),
        (RelationshipState("soldier", "player", "guarded", 0.1),),
        npc_context=soldier,
    )
    assert [action.action_type for action in actions] == ["approach", "warn", "ignore"]


def test_npc_action_is_immutable_and_validated():
    action = NpcAction("soldier", "warn", "player", {"alert": ["nearby"]}, "threat")
    assert action.parameters["alert"] == ("nearby",)
    with pytest.raises((AttributeError, TypeError)):
        action.action_type = "ignore"
    with pytest.raises(ValueError):
        NpcAction("", "warn")


def test_response_service_records_rule_selected_response_as_event_only():
    soldier = _agent("soldier", "林队长", "soldier")
    merchant = _agent("merchant", "商人", "merchant", "docks")
    minds = {"soldier": _mind("soldier", "soldier")}
    context = SimpleNamespace(
        agent_contexts=(soldier, merchant),
        character_minds=minds,
        knowledge_retriever=None,
    )
    service = NpcResponseService(id_factory=lambda: "response", clock=lambda: "now")
    responses = service.handle_event_with_context(_event(), context)
    assert len(responses) == 1
    response = responses[0]
    assert response.event_type == "npc_warn"
    assert response.actor_id == "soldier"
    assert response.target_id == "player"
    assert response.payload["source_event_id"] == "e1"
    assert response.timestamp == "2026-10-12T12:00:00+00:00"
    assert dict(soldier.world_state) == {"location": "market"}
    assert dict(merchant.world_state) == {"location": "docks"}


def test_non_security_npc_does_not_take_weapon_response_action():
    doctor = _agent("doctor", "医生", "doctor")
    minds = {"doctor": _mind("doctor", "doctor")}
    context = SimpleNamespace(agent_contexts=(doctor,), character_minds=minds, knowledge_retriever=None)
    assert NpcResponseService().handle_event_with_context(_event(), context) == ()

