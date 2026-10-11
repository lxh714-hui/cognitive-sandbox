from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from cognitive_sandbox.application.roleplay_turn_controller import RoleplayTurnController
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.roleplay_result import RoleplayResult
from cognitive_sandbox.domain.roleplay_turn import RoleplayTurn


class RoleplaySession:
    """Manage roleplay turn state and carry successful results into later turns."""

    def __init__(
        self,
        player_id: str,
        turn_controller: RoleplayTurnController,
        executor: Any,
        agent_context: AgentContext,
        world_state: Mapping[str, Any],
        situation: str = "当前场景",
        target: AgentContext | None = None,
    ) -> None:
        if not isinstance(player_id, str) or not player_id.strip():
            raise ValueError("player_id must not be empty.")
        if not isinstance(turn_controller, RoleplayTurnController):
            raise TypeError("turn_controller must be a RoleplayTurnController.")
        if not callable(getattr(executor, "execute", None)):
            raise TypeError("executor must provide an execute method.")
        if not isinstance(agent_context, AgentContext):
            raise TypeError("agent_context must be an AgentContext.")
        if agent_context.character_id != player_id:
            raise ValueError("player_id must match agent_context.character_id.")
        if not isinstance(world_state, Mapping):
            raise TypeError("world_state must be a mapping.")
        if not isinstance(situation, str):
            raise TypeError("situation must be a string.")
        if target is not None and not isinstance(target, AgentContext):
            raise TypeError("target must be an AgentContext or None.")

        self.player_id = player_id
        self.turn_controller = turn_controller
        self.current_turn: RoleplayTurn | None = None
        self.executor = executor
        self.agent_context = agent_context
        self.world_state = deepcopy(dict(world_state))
        self.situation = situation
        self.target = target
        self.last_result: RoleplayResult | None = None

    def start(self) -> RoleplayTurn:
        if self.current_turn is not None and self.current_turn.status != "completed":
            raise ValueError("the current roleplay turn has not completed.")
        self.current_turn = self.turn_controller.create_turn(self.player_id)
        return self.current_turn

    def submit_input(self, text: str) -> RoleplayTurn:
        if self.current_turn is None:
            raise ValueError("start the roleplay session before submitting input.")
        self.current_turn = self.turn_controller.submit_input(self.current_turn, text)
        return self.current_turn

    def confirm(self) -> RoleplayResult:
        if self.current_turn is None:
            raise ValueError("start the roleplay session before confirming a turn.")

        # The controller performs the input-ready transition and action parsing;
        # the executor owns the actual simulation and presentation pipeline.
        self.turn_controller.confirm_turn(self.current_turn)
        executing_turn = self.turn_controller.get_turn(self.current_turn.turn_id)
        self.current_turn = executing_turn
        result = self.executor.execute(
            executing_turn,
            self.agent_context,
            self.world_state,
            self.situation,
            self.target,
        )
        self.current_turn = self.turn_controller.complete_turn(executing_turn)
        self.last_result = result

        simulation_result = result.simulation_result
        if simulation_result is not None:
            self.agent_context = simulation_result.agent_context
            # SimulationTickResult contains the immutable state snapshot already;
            # copy only the outer mapping to keep the session's reference private.
            self.world_state = dict(simulation_result.world_state)
        return result
