from __future__ import annotations

from cognitive_sandbox.domain.dialogue import DialogueLine
from cognitive_sandbox.domain.actions import ActionCandidate, ResolvedActionResult
from cognitive_sandbox.domain.roleplay_result import RoleplayResult
from cognitive_sandbox.domain.simulation_result import SimulationTickResult
from cognitive_sandbox.application.action_event_adapter import ActionEventAdapter
from cognitive_sandbox.application.action_resolver import ActionResolver
from cognitive_sandbox.application.world_state_applier import WorldStateApplier
from cognitive_sandbox.application.world_state_updater import WorldStateUpdater
from uuid import uuid4


class SimulationActionHandler:
    """Adapt supported legacy actions to the existing SimulationTick pipeline."""

    _CUES = {"help": "病人受伤，需要救助（help）", "protect": "危险，敌人正在攻击（danger）"}
    _DIALOGUE_CUES = {"help": "help", "protect": "danger"}
    _EXPECTED = {"help": "help_attempt", "protect": "protect_attempt"}

    def handle(self, action, context) -> RoleplayResult:
        cue = self._CUES.get(action.intent)
        situation = f"{context.situation} {cue}".strip() if cue else context.situation
        result = context.simulation_tick.run(context.agent_context, context.world_state, situation)
        if not isinstance(result, SimulationTickResult):
            raise TypeError("simulation_tick.run must return SimulationTickResult")
        expected = self._EXPECTED.get(action.intent)
        if expected is None or not any(event.event_type == expected for event in result.events):
            # SimulationTick's autonomous decision policy may choose another
            # action for a player whose role does not match that policy. Resolve
            # the explicit player ActionIntent through the existing deterministic
            # action rules and world transition services instead.
            candidate = ActionCandidate(
                action_type=action.intent,
                actor_id=action.actor_id,
                intent=action.intent,
                target=action.target,
                target_refs=(action.target,) if action.target else (),
                metadata=dict(action.parameters),
                motivation="player_intent",
            )
            resolved = ActionResolver().resolve(candidate, context.world_state)
            if not isinstance(resolved, ResolvedActionResult):
                raise TypeError("ActionResolver must return a ResolvedActionResult")
            adapter = ActionEventAdapter(
                world_id=context.world_id,
                branch_id=context.branch_id,
                world_revision=0,
                location=context.world_state.get("location") if isinstance(context.world_state.get("location"), str) else None,
            )
            event = adapter.adapt(resolved, candidate)
            transition = WorldStateUpdater().update(event, context.world_state)
            state = WorldStateApplier().apply(context.world_state, transition)
            result = SimulationTickResult(state, context.agent_context, (event,), candidate)
            if not resolved.success:
                return RoleplayResult(context.turn.turn_id, False, (), (), result, resolved.event_description)
        narratives = tuple(
            narrative for event in result.events
            if (narrative := context.narrative_formatter.format(event)) is not None
        )
        dialogue = None
        service = context.dialogue_service
        if service is not None:
            situation = f"{context.situation} {self._DIALOGUE_CUES[action.intent]}".strip()
            generate = getattr(service, "generate_with_context", None)
            if callable(generate):
                dialogue = generate(
                    context.agent_context, context.target, situation,
                    character_mind=(context.character_minds or {}).get(context.agent_context.character_id),
                    current_event="；".join(item.description for item in narratives),
                    current_scene=(context.narrative_context or {"situation": context.situation}),
                    authority_context=(
                        context.authority_manager.ai_authority_context(context.agent_context.character_id)
                        if context.authority_manager is not None else None
                    ),
                )
            else:
                dialogue = service.generate(context.agent_context, context.target, situation)
        lines = (dialogue,) if isinstance(dialogue, DialogueLine) else ()
        return RoleplayResult(context.turn.turn_id, True, narratives, lines, result)
