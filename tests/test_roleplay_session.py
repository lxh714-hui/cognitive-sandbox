from itertools import count

import pytest

from cognitive_sandbox.application.action_decision import ActionDecisionEngine
from cognitive_sandbox.application.action_event_adapter import ActionEventAdapter
from cognitive_sandbox.application.action_resolver import ActionResolver
from cognitive_sandbox.application.agent_context_builder import AgentContextBuilder
from cognitive_sandbox.application.agent_state_updater import AgentStateUpdater
from cognitive_sandbox.application.dialogue_generator import DialogueGenerator
from cognitive_sandbox.application.memory_updater import MemoryUpdater
from cognitive_sandbox.application.narrative_formatter import NarrativeFormatter
from cognitive_sandbox.application.player_action_parser import PlayerActionParser
from cognitive_sandbox.application.relationship_updater import RelationshipUpdater
from cognitive_sandbox.application.roleplay_executor import RoleplayExecutor
from cognitive_sandbox.application.roleplay_session import RoleplaySession
from cognitive_sandbox.application.roleplay_turn_controller import RoleplayTurnController
from cognitive_sandbox.application.simulation_tick import SimulationTick
from cognitive_sandbox.application.world_state_applier import WorldStateApplier
from cognitive_sandbox.application.world_state_updater import WorldStateUpdater
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.agent_state import AgentDynamicState
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.domain.relationship import RelationshipState


def make_context():
    character = CharacterState("player-1", "玩家", "医生", ("compassionate",), (), (), ())
    return AgentContext(
        "player-1",
        character,
        (),
        (RelationshipState("player-1", "doctor", "care", 0.5),),
        {"social_trust": 0.5},
        AgentDynamicState("player-1", 0.5, 0.1, 0.6),
    )


def make_executor():
    event_ids = count(1)
    action_ids = count(1)
    tick = SimulationTick(
        ActionDecisionEngine(action_id_factory=lambda: f"action-{next(action_ids)}"),
        ActionResolver(),
        ActionEventAdapter(
            world_id="world-1",
            branch_id="main",
            world_revision=1,
            event_id_factory=lambda: f"event-{next(event_ids)}",
        ),
        WorldStateUpdater(),
        WorldStateApplier(),
        MemoryUpdater(memory_id_factory=lambda: "memory-1"),
        RelationshipUpdater(),
        AgentStateUpdater(),
        AgentContextBuilder(),
    )
    return RoleplayExecutor(PlayerActionParser(), tick, NarrativeFormatter(), DialogueGenerator())


def make_session():
    ids = count(1)
    initial_context = make_context()
    initial_world = {"social_trust": 0.5}
    session = RoleplaySession(
        "player-1",
        RoleplayTurnController(turn_id_factory=lambda: f"turn-{next(ids)}"),
        make_executor(),
        initial_context,
        initial_world,
        "有人受伤",
    )
    return session, initial_context, initial_world


def test_session_starts_submits_and_executes_a_turn():
    session, original_context, original_world = make_session()
    turn = session.start()
    assert turn.status == "waiting_input"

    submitted = session.submit_input("帮助医生")
    assert submitted.status == "input_ready"
    result = session.confirm()

    assert result.action_executed is True
    assert result.turn_id == turn.turn_id
    assert result.narrative_events[0].title == "一次帮助"
    assert result.dialogue_lines[0].text == "我只是做了应该做的事。"
    assert session.current_turn.status == "completed"
    assert session.last_result is result
    assert session.world_state["social_trust"] == pytest.approx(0.6)
    # This package has no memory seed for the player; the engine must not infer
    # biography from the character's occupation.
    assert session.agent_context.memories == ()
    assert original_context.memories == ()
    assert original_context.world_state["social_trust"] == 0.5
    assert original_world == {"social_trust": 0.5}


def test_session_can_start_another_turn_after_completion():
    session, _context, _world = make_session()
    first = session.start()
    session.submit_input("观察周围")
    session.confirm()
    second = session.start()

    assert first.status == "waiting_input"
    assert second.status == "waiting_input"
    assert second.turn_id != first.turn_id


def test_session_rejects_submit_before_start():
    session, _context, _world = make_session()
    with pytest.raises(ValueError, match="start the roleplay session"):
        session.submit_input("帮助")
