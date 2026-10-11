from __future__ import annotations

from PySide6.QtCore import QSettings

from cognitive_sandbox.application.ai_action_interpreter import AIActionInterpreter
from cognitive_sandbox.application.ai_gm_adapter import AIGMAdapter
from cognitive_sandbox.application.llm_provider import HTTPTransport, LLMProvider
from cognitive_sandbox.domain.llm_config import LLMConfig


class AIRuntimeWiring:
    """Build the action interpreter from saved desktop AI settings."""

    SETTINGS_PREFIX = "ai"
    SUPPORTED_PROVIDERS = frozenset({"openai-compatible", "local-compatible"})

    def __init__(
        self,
        *,
        settings: QSettings | None = None,
        transport: HTTPTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._settings = (
            settings
            if settings is not None
            else QSettings("CognitiveSandbox", "CognitiveSandbox")
        )
        self._transport = transport
        self._timeout = timeout

    def load_config(self) -> LLMConfig:
        """Read persisted provider/model/URL; API keys are deliberately absent."""
        provider = str(self._settings.value(f"{self.SETTINGS_PREFIX}/provider", "openai-compatible"))
        if provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(f"unsupported AI provider: {provider}")
        model_name = str(self._settings.value(f"{self.SETTINGS_PREFIX}/model_name", "gpt-4o-mini"))
        base_url = str(
            self._settings.value(
                f"{self.SETTINGS_PREFIX}/base_url",
                "https://api.openai.com/v1",
            )
        )
        return LLMConfig(api_key="", base_url=base_url, model_name=model_name)

    def create_action_interpreter(self) -> AIActionInterpreter:
        """Return a configured AI parser, or the keyword-only fallback if unavailable."""
        required_settings = (
            f"{self.SETTINGS_PREFIX}/provider",
            f"{self.SETTINGS_PREFIX}/model_name",
            f"{self.SETTINGS_PREFIX}/base_url",
        )
        if not all(self._settings.contains(key) for key in required_settings):
            return AIActionInterpreter()
        try:
            config = self.load_config()
            provider = LLMProvider(
                config,
                transport=self._transport,
                timeout=self._timeout,
            )
        except (TypeError, ValueError):
            return AIActionInterpreter()
        return AIActionInterpreter(AIGMAdapter(provider))
