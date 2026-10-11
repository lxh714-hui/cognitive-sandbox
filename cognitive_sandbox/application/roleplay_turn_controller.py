from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from uuid import uuid4

from cognitive_sandbox.application.player_action_parser import PlayerActionParser
from cognitive_sandbox.domain.player_action import PlayerAction
from cognitive_sandbox.domain.roleplay_turn import RoleplayTurn


class RoleplayTurnController:
    """Manage immutable turn snapshots and parse player input after confirmation."""

    def __init__(
        self,
        parser: PlayerActionParser | None = None,
        *,
        turn_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._parser = parser or PlayerActionParser()
        self._turn_id_factory = turn_id_factory or (lambda: f"turn_{uuid4().hex}")
        self._turns: dict[str, RoleplayTurn] = {}

    def create_turn(self, player_id: str) -> RoleplayTurn:
        if not isinstance(player_id, str) or not player_id.strip():
            raise ValueError("player_id must not be empty.")
        turn_id = self._turn_id_factory()
        if not isinstance(turn_id, str) or not turn_id.strip():
            raise ValueError("turn_id_factory must return a non-empty string.")
        if turn_id in self._turns:
            raise ValueError("turn_id_factory returned a duplicate turn ID.")
        turn = RoleplayTurn(turn_id, player_id, "waiting_input")
        self._turns[turn_id] = turn
        return turn

    def submit_input(self, turn: RoleplayTurn, raw_input: str) -> RoleplayTurn:
        current = self._current(turn)
        if current.status not in {"waiting_input", "input_ready"}:
            raise ValueError("input can only be changed before turn execution.")
        if not isinstance(raw_input, str) or not raw_input.strip():
            raise ValueError("raw_input must not be empty.")
        updated = replace(current, status="input_ready", player_input=raw_input)
        self._turns[turn.turn_id] = updated
        return updated

    def confirm_turn(self, turn: RoleplayTurn) -> PlayerAction | None:
        current = self._current(turn)
        if current.status != "input_ready" or current.player_input is None or not current.player_input.strip():
            raise ValueError("turn cannot be confirmed without submitted input.")
        self._turns[turn.turn_id] = replace(current, status="executing")
        return self._parser.parse(current.player_id, current.player_input)

    def complete_turn(self, turn: RoleplayTurn) -> RoleplayTurn:
        current = self._current(turn)
        if current.status != "executing":
            raise ValueError("only an executing turn can be completed.")
        completed = replace(current, status="completed")
        self._turns[turn.turn_id] = completed
        return completed

    def get_turn(self, turn_id: str) -> RoleplayTurn:
        """Return the latest immutable snapshot for a managed turn."""
        try:
            return self._turns[turn_id]
        except KeyError as error:
            raise KeyError(f"Unknown roleplay turn: {turn_id}") from error

    def _current(self, turn: RoleplayTurn) -> RoleplayTurn:
        if not isinstance(turn, RoleplayTurn):
            raise TypeError("turn must be a RoleplayTurn.")
        current = self._turns.get(turn.turn_id)
        if current is None:
            raise ValueError("turn is not managed by this controller.")
        if current.player_id != turn.player_id:
            raise ValueError("turn player_id does not match the managed turn.")
        return current
