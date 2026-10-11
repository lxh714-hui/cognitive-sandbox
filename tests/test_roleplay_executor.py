from dataclasses import FrozenInstanceError

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
from cognitive_sandbox.application.simulation_tick import SimulationTick
from cognitive_sandbox.application.world_state_applier import WorldStateApplier
from cognitive_sandbox.application.world_state_updater import WorldStateUpdater
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.agent_state import AgentDynamicState
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.domain.relationship import RelationshipState
from cognitive_sandbox.domain.roleplay_result import RoleplayResult
from cognitive_sandbox.domain.roleplay_turn import RoleplayTurn


def _context():
    character = CharacterState("player-1", "玩家", "医生", ("compassionate",), (), (), ())
    return AgentContext(
        "player-1",
        character,
        (),
        (RelationshipState("player-1", "doctor", "care", 0.5),),
        {"social_trust": 0.5},
        AgentDynamicState("player-1", 0.5, 0.1, 0.6),
    )


def _executor():
    tick = SimulationTick(
        ActionDecisionEngine(action_id_factory=iter(("action-1", "action-2")).__next__),
        ActionResolver(),
        ActionEventAdapter(
            world_id="world-1",
            branch_id="main",
            world_revision=1,
            event_id_factory=lambda: "event-1",
        ),
        WorldStateUpdater(),
        WorldStateApplier(),
        MemoryUpdater(memory_id_factory=lambda: "memory-1"),
        RelationshipUpdater(),
        AgentStateUpdater(),
        AgentContextBuilder(),
    )
    return RoleplayExecutor(PlayerActionParser(), tick, NarrativeFormatter(), DialogueGenerator())


def _turn(raw_input="帮助医生", status="executing"):
    return RoleplayTurn("turn-1", "player-1", status, raw_input)


def test_player_help_action_runs_tick_and_generates_narrative_and_dialogue():
    context = _context()
    world_state = {"social_trust": 0.5}

    result = _executor().execute(_turn(), context, world_state, "有人受伤")

    assert result.action_executed is True
    assert result.turn_id == "turn-1"
    assert result.narrative_events[0].title == "一次帮助"
    assert result.narrative_events[0].source_event_id == "event-1"
    assert result.dialogue_lines[0].text == "我只是做了应该做的事。"
    assert result.dialogue_lines[0].speaker_id == "player-1"
    assert result.simulation_result.world_state["social_trust"] == pytest.approx(0.6)
    assert context.world_state["social_trust"] == 0.5
    assert world_state["social_trust"] == 0.5


def test_protect_action_uses_existing_tick_and_narrative_pipeline():
    context = _context()
    # The player's intent is parsed from the submitted text and cues the soldier rule.
    soldier = AgentContext(
        "player-1",
        CharacterState("player-1", "玩家", "士兵", ("brave",), (), (), ()),
        (),
        (),
        {},
    )
    result = _executor().execute(_turn("保护士兵"), soldier, {}, "发现危险")

    assert result.action_executed is True
    assert result.narrative_events[0].title == "一次保护"
    assert result.dialogue_lines[0].text == "退后，我来处理。"


def test_invalid_turn_returns_failure_without_running_pipeline():
    result = _executor().execute(_turn(status="waiting_input"), _context(), {}, "有人受伤")

    assert result == RoleplayResult("turn-1", False, (), ())


def test_unrecognized_player_input_returns_failure():
    result = _executor().execute(_turn("我想休息"), _context(), {}, "安静")

    assert result.action_executed is False
    assert result.narrative_events == ()
    assert result.dialogue_lines == ()


def test_executor_does_not_mutate_turn_or_agent_inputs():
    turn = _turn()
    context = _context()
    initial_world_state = {"social_trust": 0.5}

    _executor().execute(turn, context, initial_world_state, "有人受伤")

    assert turn.status == "executing"
    assert turn.player_input == "帮助医生"
    assert context.memories == ()
    assert context.relationships[0].trust == 0.5
    assert context.dynamic_state.confidence == 0.5
    assert initial_world_state["social_trust"] == 0.5


def test_roleplay_result_is_immutable_and_uses_tuples():
    result = _executor().execute(_turn(), _context(), {}, "有人受伤")

    assert isinstance(result.narrative_events, tuple)
    assert isinstance(result.dialogue_lines, tuple)
    with pytest.raises(FrozenInstanceError):
        result.action_executed = False
