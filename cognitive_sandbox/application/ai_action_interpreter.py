from __future__ import annotations

from cognitive_sandbox.application.ai_gm_adapter import AIGMAdapter
from cognitive_sandbox.application.player_action_parser import PlayerActionParser
from cognitive_sandbox.domain.player_action import PlayerAction
from cognitive_sandbox.domain.player_intent import PlayerIntent


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

    def interpret(self, player_id: str, raw_input: str) -> PlayerIntent | None:
        self._validate_input(player_id, raw_input)
        if not raw_input.strip():
            return None

        if self._ai_adapter is not None:
            try:
                action = self._ai_adapter.parse_player_action(
                    raw_input,
                    {"player_id": player_id},
                )
                intent = self._to_intent(action, player_id, raw_input)
                if intent is not None:
                    return intent
            except Exception:
                # Provider, transport, and malformed structured output failures
                # all use the same deterministic fallback path.
                pass

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
