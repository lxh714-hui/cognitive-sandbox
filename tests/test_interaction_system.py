from __future__ import annotations

from dataclasses import FrozenInstanceError
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from cognitive_sandbox.application.action_decision import ActionDecisionEngine
from cognitive_sandbox.application.action_event_adapter import ActionEventAdapter
from cognitive_sandbox.application.action_intent_parser import ActionIntentParser
from cognitive_sandbox.application.action_resolver import ActionResolver
from cognitive_sandbox.application.agent_context_builder import AgentContextBuilder
from cognitive_sandbox.application.agent_state_updater import AgentStateUpdater
from cognitive_sandbox.application.character_dialogue_service import CharacterDialogueService
from cognitive_sandbox.application.dialogue_generator import DialogueGenerator
from cognitive_sandbox.application.memory_updater import MemoryUpdater
from cognitive_sandbox.application.narrative_formatter import NarrativeFormatter
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
from cognitive_sandbox.domain.dialogue import DialogueLine
from cognitive_sandbox.domain.player_interaction import InteractionSource, PlayerInteraction
from cognitive_sandbox.domain.relationship import RelationshipState
from cognitive_sandbox.knowledge.models.knowledge_record import KnowledgeRecord, KnowledgeType
from cognitive_sandbox.knowledge.models.knowledge_source import KnowledgeSource
from cognitive_sandbox.knowledge.models.knowledge_visibility import KnowledgeVisibility
from cognitive_sandbox.knowledge.models.world_fact import WorldFact
from cognitive_sandbox.knowledge.retrieval.knowledge_retriever import KnowledgeRetriever
from cognitive_sandbox.knowledge.storage.knowledge_store import KnowledgeStore
from cognitive_sandbox.presentation.main_window import FoundationMainWindow
from cognitive_sandbox.presentation.ui_runtime import UIRuntime


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _context(identifier, name, role="resident", traits=()):
    character = CharacterState(identifier, name, role, tuple(traits), (), (), ())
    return AgentContext(
        identifier, character, (),
        (RelationshipState(identifier, "doctor", "care", 0.5),),
        {"location": "港区旧诊所大厅"},
        AgentDynamicState(identifier, 0.5, 0.1, 0.5),
    )


def _session(parser=None, *, store=None, ai_adapter=None):
    player = _context("player", "玩家", "幸存者")
    doctor = _context("doctor", "沈医生", "医生", ("compassionate",))
    tick = SimulationTick(
        ActionDecisionEngine(), ActionResolver(),
        ActionEventAdapter(world_id="world-7", branch_id="main", world_revision=1),
        WorldStateUpdater(), WorldStateApplier(), MemoryUpdater(),
        RelationshipUpdater(), AgentStateUpdater(), AgentContextBuilder(),
    )
    retriever = KnowledgeRetriever(store) if store is not None else None
    dialogue = CharacterDialogueService(ai_adapter, DialogueGenerator())
    executor = RoleplayExecutor(
        parser or ActionIntentParser(), tick, NarrativeFormatter(), dialogue,
        known_entities=("doctor", "沈医生", "医生"),
        knowledge_store=store,
        knowledge_retriever=retriever,
        world_id="world-7",
    )
    session = RoleplaySession(
        "player", RoleplayTurnController(), executor, player,
        {
            "location": "港区旧诊所大厅",
            "environment_description": "备用灯光忽明忽暗。",
            "visible_characters": ({"character_id": "doctor", "description": "正在检查设备"},),
            "visible_objects": ({"name": "应急电源", "description": "指示灯微弱"},),
            "energy_level": 0.2,
        },
        "港区旧诊所大厅",
        agent_contexts=(player, doctor),
        world_instance_id="world-7",
    )
    session.knowledge_store = store
    session.knowledge_retriever = retriever
    return session


def test_text_input_becomes_text_interaction_and_open_intent(qapp):
    window = FoundationMainWindow()
    runtime = UIRuntime(window, _session())

    runtime.handle_player_input("和沈医生交谈")
    assert runtime.session.pending_interaction.source is InteractionSource.TEXT
    assert runtime.session.pending_interaction.raw_input == "和沈医生交谈"
    result = runtime.session.confirm()

    assert result.action_executed
    assert result.simulation_result.events[0].event_type == "dialogue_event"
    window.close()


def test_button_wait_generates_wait_interaction_without_ai_call(qapp):
    class NoAI:
        def interpret_action(self, *_args):
            raise AssertionError("button action must bypass AI")

    window = FoundationMainWindow()
    runtime = UIRuntime(window, _session(parser=NoAI()))
    runtime.handle_interaction_button("wait")

    assert runtime.last_result.action_executed
    event = runtime.last_result.simulation_result.events[0]
    assert event.event_type == "wait_elapsed"
    assert runtime.session.world_state["elapsed_minutes"] == 10
    assert "等待了一段时间" in window.narrative_display.toPlainText()
    window.close()


def test_talk_runs_as_action_and_uses_target_scoped_knowledge(qapp):
    parsed_question = ActionIntentParser().parse("player", "我问医生备用电源的情况")
    assert parsed_question.intent == "ask"
    assert parsed_question.target == "医生"
    assert parsed_question.parameters["topic"] == "备用电源"
    store = KnowledgeStore()
    fact = WorldFact("fact_energy", "备用电源已经接近耗尽", "observation", "now")
    store.add_fact(fact)
    store.add_knowledge(KnowledgeRecord(
        "doctor", "fact_energy", KnowledgeType.OBSERVED,
        KnowledgeSource("source_1", "observation", "现场观察"), 0.9, "now",
        "备用电源已经接近耗尽", KnowledgeVisibility(),
    ))

    class RecordingDialogue:
        def __init__(self):
            self.seen = None

        def generate_with_context(self, speaker, target, _situation, **kwargs):
            self.seen = (speaker.character_id, target.character_id, kwargs["knowledge_context"])
            return DialogueLine(speaker.character_id, "电源快撑不住了。", "concerned")

    dialogue = RecordingDialogue()
    session = _session(store=store)
    session.executor._dialogue_generator = dialogue
    session.start()
    session.submit_input("我问医生备用电源的情况")
    result = session.confirm()

    assert result.action_executed, result.system_message
    assert result.simulation_result.events[0].event_type == "dialogue_event"
    assert result.dialogue_lines[0].speaker_id == "doctor"
    assert dialogue.seen[0:2] == ("doctor", "player")
    assert dialogue.seen[2].owner_id == "doctor"
    assert dialogue.seen[2].records[0].known_content == "备用电源已经接近耗尽"


def test_observe_creates_private_knowledge_and_deduplicates_repeats(qapp):
    store = KnowledgeStore()
    window = FoundationMainWindow()
    runtime = UIRuntime(window, _session(store=store))

    runtime.handle_interaction_button("observe")
    first_facts, first_records = store.snapshot()
    assert runtime.last_result.simulation_result.events[0].event_type == "observe_action"
    assert first_facts
    assert all(record.owner_id == "player" for record in first_records)
    assert all(record.knowledge_type is KnowledgeType.OBSERVED for record in first_records)
    assert "沈医生" in window.narrative_display.toPlainText()
    assert "energy_level" not in window.narrative_display.toPlainText()

    runtime.handle_interaction_button("observe")
    facts, records = store.snapshot()
    assert len(facts) == len(first_facts)
    assert len(records) == len(first_records)
    window.close()


def test_ai_failure_falls_back_to_rules_and_old_actions_remain_compatible(qapp):
    class FailingAI:
        def parse_player_action(self, *_args):
            raise RuntimeError("offline")

        def parse_action_intent(self, *_args):
            raise RuntimeError("offline")

    session = _session(parser=_ai_parser(FailingAI()))
    session.start()
    session.submit_input("观察周围")
    observed = session.confirm()
    assert observed.action_executed
    assert observed.simulation_result.events[0].event_type == "observe_action"

    for text, expected in (("帮助医生", "help_attempt"), ("保护医生", "protect_attempt")):
        session.start()
        session.submit_input(text)
        result = session.confirm()
        assert result.action_executed
        assert result.simulation_result.events[0].event_type == expected


def _ai_parser(adapter):
    from cognitive_sandbox.application.ai_action_interpreter import AIActionInterpreter
    return AIActionInterpreter(adapter)


def test_player_interaction_is_immutable_and_freezes_parameters():
    source = {"topic": ["power", "supply"]}
    interaction = PlayerInteraction("player", "talk", "TEXT", "问医生", parameters=source)
    source["topic"].append("changed")

    assert interaction.parameters["topic"] == ("power", "supply")
    with pytest.raises(TypeError):
        interaction.parameters["x"] = 1
    with pytest.raises(FrozenInstanceError):
        interaction.intent = "wait"


def test_ui_exposes_execute_wait_and_observe_buttons(qapp):
    window = FoundationMainWindow()

    assert window.confirm_button.text() == "执行"
    assert window.findChild(type(window.wait_button), "waitButton") is window.wait_button
    assert window.findChild(type(window.observe_button), "observeButton") is window.observe_button
    window.close()
