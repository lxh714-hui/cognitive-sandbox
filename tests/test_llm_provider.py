from dataclasses import FrozenInstanceError
import json

import pytest

from cognitive_sandbox.application.llm_provider import LLMProvider
from cognitive_sandbox.domain.ai_gm import AIGMRequest, AIGMResponse
from cognitive_sandbox.domain.llm_config import LLMConfig


class MockHTTPTransport:
    def __init__(self, response=None, error=None):
        self.response = response or {"choices": [{"message": {"content": "模型生成文本"}}]}
        self.error = error
        self.calls = []

    def post(self, url, *, headers, body, timeout):
        self.calls.append((url, dict(headers), body, timeout))
        if self.error is not None:
            raise self.error
        return self.response


def _config():
    return LLMConfig("secret-token", "https://example.test/v1", "test-model")


def test_llm_config_is_immutable_and_does_not_reveal_api_key_in_repr():
    config = _config()

    assert config.base_url == "https://example.test/v1"
    assert config.model_name == "test-model"
    assert "secret-token" not in repr(config)
    with pytest.raises(FrozenInstanceError):
        config.model_name = "other-model"


def test_provider_sends_openai_chat_completions_request_format():
    transport = MockHTTPTransport()
    provider = LLMProvider(_config(), transport=transport, timeout=5)
    request = AIGMRequest("generate_narrative", {"event": "a cup broke"})

    response = provider.complete(request)

    url, headers, body, timeout = transport.calls[0]
    assert url == "https://example.test/v1/chat/completions"
    assert headers["Authorization"] == "Bearer secret-token"
    assert headers["Content-Type"] == "application/json"
    assert body["model"] == "test-model"
    assert body["messages"][0]["role"] == "system"
    user_message = json.loads(body["messages"][1]["content"])
    assert user_message == {"request_type": "generate_narrative", "context": {"event": "a cup broke"}}
    assert timeout == 5
    assert response == AIGMResponse("模型生成文本")


def test_provider_parses_openai_response_content():
    transport = MockHTTPTransport(
        {"choices": [{"message": {"content": [{"type": "text", "text": "第一段"}, {"type": "text", "text": "第二段"}]}}]}
    )

    response = LLMProvider(_config(), transport=transport).complete(AIGMRequest("test", {}))

    assert response.content == "第一段第二段"


@pytest.mark.parametrize(
    ("response", "message"),
    [
        ({"error": {"message": "invalid key"}}, "invalid key"),
        ({"choices": []}, "missing choices"),
    ],
)
def test_provider_returns_clear_error_response_for_api_errors(response, message):
    provider = LLMProvider(_config(), transport=MockHTTPTransport(response))

    result = provider.complete(AIGMRequest("test", {}))

    assert result.content.startswith("LLM provider error:")
    assert message in result.content


def test_provider_converts_transport_exception_to_error_response():
    provider = LLMProvider(_config(), transport=MockHTTPTransport(error=TimeoutError("request timed out")))

    response = provider.complete(AIGMRequest("test", {}))

    assert response.content == "LLM provider error: request timed out"


def test_provider_does_not_modify_request_or_nested_input_data():
    context = {"nested": {"items": ["cup"]}}
    request = AIGMRequest("parse_player_action", context)
    transport = MockHTTPTransport()

    LLMProvider(_config(), transport=transport).complete(request)

    assert context == {"nested": {"items": ["cup"]}}
    assert request.context["nested"]["items"] == ("cup",)
