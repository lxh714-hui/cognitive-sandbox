from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cognitive_sandbox.application.player_action_parser import PlayerActionParser
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.dialogue import DialogueLine
from cognitive_sandbox.domain.narrative_event import NarrativeEvent
from cognitive_sandbox.domain.player_action import PlayerAction
from cognitive_sandbox.domain.roleplay_result import RoleplayResult
from cognitive_sandbox.domain.roleplay_turn import RoleplayTurn
from cognitive_sandbox.domain.simulation_result import SimulationTickResult


class RoleplayExecutor:
    """Orchestrate one confirmed player action through existing simulation/presentation services."""

    _EXPECTED_EVENTS = {
        "observe": "observe_action",
        "help": "help_attempt",
        "protect": "protect_attempt",
    }
    _SIMULATION_CUES = {
        "observe": "观察周围环境",
        "help": "病人受伤，需要救助（help）",
        "protect": "危险，敌人正在攻击（danger）",
    }
    _DIALOGUE_CUES = {"help": "help", "protect": "danger"}

    def __init__(
        self,
        player_action_parser: PlayerActionParser,
        simulation_tick: Any,
        narrative_formatter: Any,
        dialogue_generator: Any,
    ) -> None:
        self._parser = player_action_parser
        self._simulation_tick = simulation_tick
        self._narrative_formatter = narrative_formatter
        self._dialogue_generator = dialogue_generator

    def execute(
        self,
        turn: RoleplayTurn,
        agent_context: AgentContext,
        world_state: Mapping[str, Any],
        situation: str,
        target: AgentContext | None = None,
    ) -> RoleplayResult:
        if not isinstance(turn, RoleplayTurn):
            raise TypeError("turn must be a RoleplayTurn.")
        if not isinstance(agent_context, AgentContext):
            raise TypeError("agent_context must be an AgentContext.")
        if not isinstance(world_state, Mapping):
            raise TypeError("world_state must be a mapping.")
        if not isinstance(situation, str):
            raise TypeError("situation must be a string.")
        if target is not None and not isinstance(target, AgentContext):
            raise TypeError("target must be an AgentContext or None.")
        if turn.status != "executing" or turn.player_input is None:
            return self._failed(turn.turn_id)

        action = self._parser.parse(turn.player_id, turn.player_input)
        if action is None or not isinstance(action, PlayerAction):
            return self._failed(turn.turn_id)
        if turn.player_id != agent_context.character_id:
            raise ValueError("turn player_id must match agent_context.character_id.")

        simulation_situation = self._simulation_situation(action, situation)
        tick_result = self._simulation_tick.run(agent_context, world_state, simulation_situation)
        if not isinstance(tick_result, SimulationTickResult):
            raise TypeError("simulation_tick.run must return a SimulationTickResult.")
        expected_event = self._EXPECTED_EVENTS.get(action.intent)
        if expected_event is None or not any(
            event.event_type == expected_event for event in tick_result.events
        ):
            return self._failed(turn.turn_id)

        narratives: list[NarrativeEvent] = []
        for event in tick_result.events:
            narrative = self._narrative_formatter.format(event)
            if narrative is not None:
                narratives.append(narrative)

        dialogue_situation = f"{situation} {self._DIALOGUE_CUES.get(action.intent, '')}".strip()
        dialogue = self._dialogue_generator.generate(agent_context, target, dialogue_situation)
        dialogue_lines = (dialogue,) if isinstance(dialogue, DialogueLine) else ()
        return RoleplayResult(
            turn_id=turn.turn_id,
            action_executed=True,
            narrative_events=tuple(narratives),
            dialogue_lines=dialogue_lines,
            simulation_result=tick_result,
        )

    def _simulation_situation(self, action: PlayerAction, situation: str) -> str:
        cue = self._SIMULATION_CUES.get(action.intent)
        if cue is None:
            return situation
        return f"{situation} {cue}".strip()

    @staticmethod
    def _failed(turn_id: str) -> RoleplayResult:
        return RoleplayResult(turn_id, False, (), ())
