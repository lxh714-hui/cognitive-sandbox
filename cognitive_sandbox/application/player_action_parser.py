from __future__ import annotations

from cognitive_sandbox.domain.player_action import PlayerAction


class PlayerActionParser:
    """Map a few player text keywords to an action intent."""

    _INTENTS = (
        (("观察", "看看", "查看"), "observe"),
        (("帮助", "救"), "help"),
        (("保护", "守护"), "protect"),
    )

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

        target = "doctor" if "医生" in text else "soldier" if "士兵" in text else None
        return PlayerAction(
            player_id=player_id,
            raw_input=raw_input,
            intent=intent,
            target=target,
        )
