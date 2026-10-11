from __future__ import annotations

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QListWidget, QPlainTextEdit, QPushButton

from cognitive_sandbox.application.ai_gm_adapter import AIGMAdapter
from cognitive_sandbox.application.ai_action_interpreter import AIActionInterpreter
from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.application.scenario_runtime_builder import ScenarioRuntimeBuilder
from cognitive_sandbox.application.world_creation_session import WorldCreationSession
from cognitive_sandbox.application.world_generator import WorldGenerator
from cognitive_sandbox.application.world_bootstrap import WorldBootstrap
from cognitive_sandbox.domain.ai_gm import AIGMResponse
from cognitive_sandbox.presentation.main_window import FoundationMainWindow


def world_json() -> str:
    value = {
        "world": {
            "world_id": "harbor_playtest",
            "name": "雾港",
            "description": "风暴后的海港诊所。",
            "history": ["风暴在昨夜登陆。"],
            "rules": ["资源有限。"],
        },
        "characters": [
            {
                "character_id": character_id,
                "name": name,
                "identity": {"occupation": occupation},
                "personality": traits,
                "background": "在风暴后留在港区。",
                "goals": goals,
                "constraints": [],
            }
            for character_id, name, occupation, traits, goals in (
                ("doctor", "林医生", "医生", ["compassionate"], ["帮助他人"]),
                ("soldier", "陈队长", "士兵", ["brave"], ["保护居民"]),
                ("survivor", "阿禾", "居民", ["adaptive"], ["寻找物资"]),
            )
        ],
        "events": [
            {
                "event_id": "clinic_power",
                "name": "诊所断电",
                "description": "诊所的灯光熄灭，备用电源仍可尝试启动。",
                "event_type": "initial",
                "participants": ["doctor"],
                "conditions": ["night"],
                "effects": ["可能影响诊疗"],
                "priority": 1,
            }
        ],
    }
    return json.dumps(value, ensure_ascii=False)


class WorldProvider:
    def __init__(self) -> None:
        self.input_json = world_json()
        self.requests = []

    def complete(self, request) -> AIGMResponse:
        self.requests.append(request)
        return AIGMResponse(self.input_json)


class ActionProvider:
    def __init__(self) -> None:
        self.requests = []

    def complete(self, request) -> AIGMResponse:
        self.requests.append(request)
        return AIGMResponse(json.dumps({"intent": "help", "target": None}))


class CapturingRuntimeBuilder:
    def __init__(self) -> None:
        self.inner = ScenarioRuntimeBuilder(
            world_bootstrap=WorldBootstrap(world_id_factory=lambda: "runtime-world")
        )
        self.built_runtime = None

    def build(self, content):
        self.built_runtime = self.inner.build(content)
        return self.built_runtime


@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])


def test_generated_world_is_confirmed_started_and_played_through_ai(qapp, monkeypatch) -> None:
    world_provider = WorldProvider()
    action_provider = ActionProvider()
    runtime_builder = CapturingRuntimeBuilder()
    launcher = GameLauncher(
        action_interpreter=AIActionInterpreter(AIGMAdapter(action_provider)),
        scenario_runtime_builder=runtime_builder,
    )
    creation = WorldCreationSession(WorldGenerator(world_provider), launcher)
    source_prompt = "风暴后的海港诊所"
    before_json = world_provider.input_json

    generated = creation.generate(source_prompt)
    assert generated.validation_result.valid
    assert creation.state == WorldCreationSession.DRAFT
    assert launcher.current_session is None

    creation.confirm()
    session = creation.start()

    assert creation.state == WorldCreationSession.STARTED
    assert runtime_builder.built_runtime is not None
    assert len(runtime_builder.built_runtime.agent_contexts) == 3
    assert [agent.character_id for agent in runtime_builder.built_runtime.agent_contexts] == [
        "doctor", "soldier", "survivor"
    ]
    assert runtime_builder.built_runtime.initial_events[0].event_id == "clinic_power"
    assert session.agent_context.character_id == "doctor"
    assert session.last_result is None  # initial event cards are held, not executed

    raw_input = "请帮助受伤的病人"
    session.submit_input(raw_input)
    roleplay_result = session.confirm()

    assert roleplay_result.action_executed
    assert roleplay_result.simulation_result.events[0].event_type == "help_attempt"
    assert action_provider.requests[0].request_type == "parse_player_action"
    assert action_provider.requests[0].context["player_text"] == raw_input
    assert raw_input == "请帮助受伤的病人"
    assert source_prompt == "风暴后的海港诊所"
    assert world_provider.input_json == before_json

    # Exercise the lightweight create-world UI and confirm it attaches the launched session.
    ui_launcher = GameLauncher(action_interpreter=AIActionInterpreter(AIGMAdapter(ActionProvider())))
    ui_creation = WorldCreationSession(WorldGenerator(WorldProvider()), ui_launcher)
    monkeypatch.setattr(ui_launcher, "create_world_creation_session", lambda: ui_creation)
    window = FoundationMainWindow()
    window.set_game_launcher(ui_launcher)
    dialog: QDialog = window._create_ai_world_creation_dialog()
    dialog.findChild(QPlainTextEdit, "worldPrompt").setPlainText("风暴后的海港诊所")
    dialog.findChild(QPushButton, "generateWorldButton").click()

    assert dialog.findChild(QLabel, "worldDraftName").text() == "雾港"
    assert dialog.findChild(QListWidget, "worldDraftCharacters").count() == 3
    assert dialog.findChild(QListWidget, "worldDraftEvents").count() == 1
    confirm_button = dialog.findChild(QPushButton, "confirmWorldCreationButton")
    assert confirm_button.isEnabled()
    confirm_button.click()

    assert ui_creation.state == WorldCreationSession.STARTED
    assert window.current_session is ui_launcher.current_session
    assert window.ui_runtime.session is window.current_session
    window.close()
    dialog.close()
