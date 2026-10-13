from __future__ import annotations

import logging
import re

from cognitive_sandbox.application.ai_gm_adapter import AIGMAdapter
from cognitive_sandbox.application.player_action_parser import PlayerActionParser
from cognitive_sandbox.application.action_intent_parser import ActionIntentParser
from cognitive_sandbox.domain.action_intent import ActionIntent
from cognitive_sandbox.domain.player_action import PlayerAction
from cognitive_sandbox.domain.player_intent import PlayerIntent

logger = logging.getLogger(__name__)


class AIActionInterpreter:
    """Interpret player text into a safe, structured intent.

    The adapter only receives the player ID and submitted text. It never receives
    world state or decides the consequences of an action. Invalid AI output or
    provider failures fall back to the deterministic keyword parser.
    """

    def __init__(
        self,
        ai_adapter: AIGMAdapter | None = None,
        fallback_parser: PlayerActionParser | None = None,
    ) -> None:
        if ai_adapter is not None and not callable(
            getattr(ai_adapter, "parse_player_action", None)
        ):
            raise TypeError("ai_adapter must provide parse_player_action.")
        if fallback_parser is not None and not callable(
            getattr(fallback_parser, "parse", None)
        ):
            raise TypeError("fallback_parser must provide parse.")
        self._ai_adapter = ai_adapter
        self._fallback_parser = fallback_parser or PlayerActionParser()
        self._action_intent_fallback = ActionIntentParser()

    def interpret_action(self, actor_id: str, raw_input: str) -> ActionIntent | None:
        """Return an open-vocabulary intent; no world state is provided to the AI."""
        self._validate_input(actor_id, raw_input)
        if not raw_input.strip():
            return None
        # Short conversational prompts that ask for guidance are not gameplay
        # actions. Resolve them locally so a model cannot turn uncertainty into
        # an invented action or a world-changing proposal.
        guidance = self._action_intent_fallback.parse(actor_id, raw_input)
        if guidance is not None and guidance.intent == "seek_guidance":
            return guidance
        method = getattr(self._ai_adapter, "parse_action_intent", None)
        if callable(method):
            try:
                action = method(raw_input, _player_authority_context(actor_id))
                if action is not None:
                    if not isinstance(action, ActionIntent):
                        raise TypeError("AI adapter must return ActionIntent or None.")
                    if action.actor_id != actor_id or action.raw_input != raw_input:
                        raise ValueError("structured action does not match submitted input.")
                    local_hints = self._action_intent_fallback.parse(actor_id, raw_input)
                    if local_hints is not None and local_hints.parameters:
                        action = ActionIntent(
                            action.actor_id,
                            action.raw_input,
                            action.intent,
                            action.target or local_hints.target,
                            action.object or local_hints.object,
                            {**dict(action.parameters), **dict(local_hints.parameters)},
                        )
                    return action
            except Exception as error:
                reason = getattr(error, "reason", None) or type(error).__name__
                raw_response = getattr(error, "raw_response", None)
                if isinstance(raw_response, str):
                    logger.debug(
                        "AI action intent parse failed; reason=%s; raw_response=%s",
                        reason,
                        _redact_sensitive_text(raw_response),
                    )
                else:
                    logger.debug("AI action intent interpretation failed; reason=%s", reason)
        return self._action_intent_fallback.parse(actor_id, raw_input)

    def interpret(self, player_id: str, raw_input: str) -> PlayerIntent | None:
        self._validate_input(player_id, raw_input)
        if not raw_input.strip():
            return None

        if self._ai_adapter is not None:
            try:
                action = self._ai_adapter.parse_player_action(
                    raw_input,
                    _player_authority_context(player_id),
                )
                intent = self._to_intent(action, player_id, raw_input)
                if intent is not None:
                    return intent
            except Exception as error:
                # Provider, transport, and malformed structured output failures
                # all use the same deterministic fallback path.
                reason = getattr(error, "reason", None) or type(error).__name__
                raw_response = getattr(error, "raw_response", None)
                if isinstance(raw_response, str):
                    logger.debug(
                        "AI action parse failed; reason=%s; raw_response=%s",
                        reason,
                        _redact_sensitive_text(raw_response),
                    )
                else:
                    logger.debug("AI action interpretation failed; reason=%s", reason)

        fallback = self._fallback_parser.parse(player_id, raw_input)
        return self._to_intent(fallback, player_id, raw_input)

    def parse(self, player_id: str, raw_input: str) -> PlayerAction | None:
        """Provide the existing parser-compatible shape for RoleplayExecutor."""
        intent = self.interpret(player_id, raw_input)
        if intent is None:
            return None
        return PlayerAction(
            player_id=intent.player_id,
            raw_input=intent.raw_input,
            intent=intent.intent,
            target=intent.target,
        )

    @staticmethod
    def _to_intent(
        action: PlayerAction | None,
        player_id: str,
        raw_input: str,
    ) -> PlayerIntent | None:
        if action is None:
            return None
        if not isinstance(action, PlayerAction):
            raise TypeError("action parser must return PlayerAction or None.")
        if action.player_id != player_id or action.raw_input != raw_input:
            raise ValueError("structured action does not match the submitted input.")
        if action.intent not in PlayerIntent.SUPPORTED_INTENTS:
            raise ValueError("structured action contains an unsupported intent.")
        return PlayerIntent(
            player_id=player_id,
            raw_input=raw_input,
            intent=action.intent,
            target=action.target,
        )

    @staticmethod
    def _validate_input(player_id: str, raw_input: str) -> None:
        if not isinstance(player_id, str) or not player_id.strip():
            raise ValueError("player_id must not be empty.")
        if not isinstance(raw_input, str):
            raise TypeError("raw_input must be a string.")


def _redact_sensitive_text(value: str) -> str:
    """Keep useful model diagnostics while masking accidentally echoed secrets."""
    value = re.sub(r"(?i)(Bearer\s+)[A-Za-z0-9._~+/-]+", r"\1[REDACTED]", value)
    value = re.sub(
        r"(?i)(api[_-]?key|authorization|token|secret|base[_-]?url)\s*[:=]\s*([^\s,;]+)",
        r"\1=[REDACTED]",
        value,
    )
    return re.sub(r"\bsk-[A-Za-z0-9_-]{12,}\b", "[REDACTED]", value)


def _player_authority_context(player_id: str) -> dict:
    # Keep the long-standing adapter input contract. AIGMAdapter adds its
    # authority projection before constructing the actual provider request.
    return {"player_id": player_id}
