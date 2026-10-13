from __future__ import annotations

from cognitive_sandbox.domain.player_action import PlayerAction
from cognitive_sandbox.application.action_intent_parser import ActionIntentParser
from cognitive_sandbox.application.scenario_runtime_defaults import LEGACY_ENTITY_ALIASES


class PlayerActionParser:
    """Map a few player text keywords to an action intent."""

    _INTENTS = (
        (("观察", "看看", "查看"), "observe"),
        (("帮助", "救"), "help"),
        (("保护", "守护"), "protect"),
    )

    def __init__(self, *, entity_aliases=None, location_aliases=None, action_defaults=None):
        self._entity_aliases = dict(
            LEGACY_ENTITY_ALIASES if entity_aliases is None else entity_aliases
        )
        self._location_aliases = dict(location_aliases or {})
        self._action_defaults = dict(action_defaults or {})

    def with_scenario_config(self, scenario_config):
        config = scenario_config or {}
        return PlayerActionParser(
            entity_aliases=config.get("entity_aliases", {}),
            location_aliases=config.get("location_aliases", {}),
            action_defaults=config.get("action_defaults", {}),
        )

    def parse_action_intent(self, actor_id: str, raw_input: str):
        """Open-vocabulary parser used by the application execution boundary."""
        return ActionIntentParser(
            self._entity_aliases, self._location_aliases, self._action_defaults
        ).parse(actor_id, raw_input)

    def parse(self, player_id: str, raw_input: str) -> PlayerAction | None:
        if not isinstance(player_id, str) or not player_id.strip():
            raise ValueError("player_id must not be empty.")
        if not isinstance(raw_input, str):
            raise TypeError("raw_input must be a string.")

        text = raw_input.strip()
        if not text:
            return None
        intent = next(
            (
                candidate_intent
                for keywords, candidate_intent in self._INTENTS
                if any(keyword in text for keyword in keywords)
            ),
            None,
        )
        if intent is None:
            return None

        target = next((entity_id for alias, entity_id in self._entity_aliases.items()
                       if alias.casefold() in text.casefold()), None)
        return PlayerAction(
            player_id=player_id,
            raw_input=raw_input,
            intent=intent,
            target=target,
        )
