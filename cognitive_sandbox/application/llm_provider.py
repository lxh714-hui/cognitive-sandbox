from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
import json
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from cognitive_sandbox.domain.ai_gm import AIGMRequest, AIGMResponse
from cognitive_sandbox.domain.llm_config import LLMConfig


class HTTPTransport(Protocol):
    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, Any],
        timeout: float,
    ) -> Mapping[str, Any]: ...


class _UrllibTransport:
    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, Any],
        timeout: float,
    ) -> Mapping[str, Any]:
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = Request(url, data=encoded, headers=dict(headers), method="POST")
        try:
            with urlopen(request, timeout=timeout) as response:
                decoded = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            message = self._http_error_message(error)
            raise RuntimeError(f"HTTP {error.code}: {message}") from None
        except URLError as error:
            if isinstance(error.reason, TimeoutError):
                raise TimeoutError("request timed out") from None
            raise ConnectionError("could not connect to the LLM endpoint") from None
        if not isinstance(decoded, Mapping):
            raise ValueError("HTTP response must be a JSON object")
        return decoded

    @staticmethod
    def _http_error_message(error: HTTPError) -> str:
        try:
            payload = json.loads(error.read().decode("utf-8"))
            error_value = payload.get("error", {}) if isinstance(payload, dict) else {}
            if isinstance(error_value, dict) and isinstance(error_value.get("message"), str):
                return error_value["message"]
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass
        return "request was rejected"


class LLMProvider:
    """OpenAI Chat Completions-compatible provider with injectable HTTP transport."""

    def __init__(
        self,
        config: LLMConfig,
        *,
        transport: HTTPTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        if not isinstance(config, LLMConfig):
            raise TypeError("config must be an LLMConfig.")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("timeout must be a positive number.")
        if transport is not None and not callable(getattr(transport, "post", None)):
            raise TypeError("transport must provide a callable post method.")
        self._config = config
        self._transport = transport or _UrllibTransport()
        self._timeout = float(timeout)

    def complete(self, request: AIGMRequest) -> AIGMResponse:
        if not isinstance(request, AIGMRequest):
            return AIGMResponse("LLM provider error: request must be an AIGMRequest")
        try:
            headers = {"Content-Type": "application/json"}
            if self._config.api_key:
                headers["Authorization"] = f"Bearer {self._config.api_key}"
            system_prompt = "You are an AI game master. Return only the requested content."
            if request.request_type == "parse_action_intent":
                system_prompt = (
                    "Interpret only the player's requested action. Return one JSON object with "
                    "intent (an open-vocabulary short action label), target (a person explicitly "
                    "named by the player or null), object (a place or object explicitly named "
                    "by the player or null), and parameters (an object). Do not invent people, "
                    "objects, places, world changes, events, success, or outcomes. Do not execute "
                    "the action. If unclear, return {\"intent\":null}."
                )
            body = {
                "model": self._config.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "request_type": request.request_type,
                                "context": _to_json_value(request.context),
                            },
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                    },
                ],
            }
            response = self._transport.post(
                self._endpoint(),
                headers=headers,
                body=body,
                timeout=self._timeout,
            )
            return AIGMResponse(self._extract_content(response))
        except Exception as error:
            detail = str(error).strip() or error.__class__.__name__
            return AIGMResponse(f"LLM provider error: {detail}")

    def _endpoint(self) -> str:
        base_url = self._config.base_url
        if base_url.endswith("/chat/completions"):
            return base_url
        return f"{base_url}/chat/completions"

    @staticmethod
    def _extract_content(response: Mapping[str, Any]) -> str:
        if not isinstance(response, Mapping):
            raise ValueError("HTTP response must be a JSON object")
        if "error" in response:
            error = response["error"]
            if isinstance(error, Mapping):
                message = error.get("message")
            else:
                message = error
            raise RuntimeError(str(message or "remote model returned an error"))
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise ValueError("response is missing choices[0].message.content") from error
        if isinstance(content, str) and content.strip():
            return content
        if isinstance(content, list):
            text_parts = [
                item["text"]
                for item in content
                if isinstance(item, Mapping)
                and item.get("type") == "text"
                and isinstance(item.get("text"), str)
            ]
            joined = "".join(text_parts)
            if joined.strip():
                return joined
        raise ValueError("response content is empty or not text")


def _to_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _to_json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_to_json_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((_to_json_value(item) for item in value), key=repr)
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _to_json_value(getattr(value, field.name)) for field in fields(value)}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
