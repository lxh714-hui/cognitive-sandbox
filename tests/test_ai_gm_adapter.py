from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.ai_gm_adapter import AIGMAdapter, MockAIProvider
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.ai_gm import AIGMRequest, AIGMResponse
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.domain.player_action import PlayerAction
from cognitive_sandbox.domain.world_events import WorldEvent


def _agent(agent_id="agent-1", traits=("compassionate",)):
    character = CharacterState(agent_id, "林夏", "医生", traits, (), (), ())
    return AgentContext(agent_id, character, (), (), {"nested": {"items": ["cup"]}})


def _event():
    return WorldEvent("event-1", "main", "world-1", "help_attempt", "agent-1", {}, 1)


def test_ai_request_and_response_models_validate_and_freeze_context():
    source = {"nested": {"items": [1]}}
    request = AIGMRequest("test", source)
    response = AIGMResponse("mock response")

    source["nested"]["items"].append(2)
    assert request.context["nested"]["items"] == (1,)
    assert response.content == "mock response"
    with pytest.raises(TypeError):
        request.context["nested"]["items"][0] = 3
    with pytest.raises(FrozenInstanceError):
        response.content = "changed"


def test_mock_provider_returns_response_for_supported_request():
    response = MockAIProvider().complete(AIGMRequest("generate_narrative", {"event": _event()}))

    assert isinstance(response, AIGMResponse)
    assert response.content == "有人伸出了援手"


def test_player_action_parser_interface_returns_structured_action():
    action = AIGMAdapter().parse_player_action("帮助医生", {
        "player_id": "agent-1", "scenario_config": {"entity_aliases": {"医生": "doctor"}},
    })

    assert action == PlayerAction("agent-1", "帮助医生", "help", "doctor")
    assert AIGMAdapter().parse_player_action("我想休息", _agent()) is None


def test_narrative_interface_returns_text():
    text = AIGMAdapter().generate_narrative(_event(), _agent())

    assert text == "有人伸出了援手"


def test_dialogue_interface_returns_text():
    adapter = AIGMAdapter()

    assert adapter.generate_dialogue(_agent(), None, "help") == "我只是做了应该做的事。"
    assert adapter.generate_dialogue(_agent(traits=("brave",)), None, "danger") == "退后，我来处理。"


def test_adapter_does_not_modify_input_domain_objects():
    agent = _agent()
    event = _event()
    agent_world_state = agent.world_state
    event_payload = dict(event.payload)

    adapter = AIGMAdapter()
    adapter.parse_player_action("帮助医生", agent)
    adapter.generate_narrative(event, agent)
    adapter.generate_dialogue(agent, None, "help")

    assert agent.world_state == agent_world_state
    assert event.payload == event_payload
    assert agent.memories == ()
