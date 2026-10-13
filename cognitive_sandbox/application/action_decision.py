from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.application.scenario_runtime_defaults import DEFAULT_ACTION_DECISION_RULES


@dataclass(frozen=True)
class ActionDecisionInput:
    agent_context: AgentContext
    situation: str

    def __post_init__(self) -> None:
        if not isinstance(self.agent_context, AgentContext):
            raise TypeError("agent_context must be an AgentContext.")
        if not isinstance(self.situation, str) or not self.situation.strip():
            raise ValueError("situation must not be empty.")


class ActionDecisionEngine:
    """Generate immutable action candidates from role and situation keywords."""

    def __init__(self, *, action_id_factory: Callable[[], str] | None = None, action_rules=None) -> None:
        self._action_id_factory = action_id_factory or (lambda: f"action_{uuid4().hex}")
        self._action_rules = tuple(DEFAULT_ACTION_DECISION_RULES if action_rules is None else action_rules)

    def generate(self, decision_input: ActionDecisionInput) -> tuple[ActionCandidate, ...]:
        if not isinstance(decision_input, ActionDecisionInput):
            raise TypeError("decision_input must be an ActionDecisionInput.")

        context = decision_input.agent_context
        situation = decision_input.situation.casefold()
        role = context.character_state.role.casefold()
        specific = None
        for rule in self._action_rules:
            role_aliases = tuple(str(item).casefold() for item in rule.get("role_aliases", ()))
            situation_aliases = tuple(str(item).casefold() for item in rule.get("situation_aliases", ()))
            if (any(alias in role for alias in role_aliases)
                    and any(keyword in situation for keyword in situation_aliases)):
                specific = (str(rule["intent"]), str(rule.get("motivation", "goal")))
                break

        candidates: list[ActionCandidate] = []
        if specific is not None:
            candidates.append(self._candidate(context.character_id, *specific))
        candidates.append(self._candidate(context.character_id, "observe", "curiosity"))
        return tuple(candidates)

    def _candidate(self, actor_id: str, intent: str, motivation: str) -> ActionCandidate:
        action_id = self._action_id_factory()
        if not isinstance(action_id, str) or not action_id.strip():
            raise ValueError("action_id_factory must return a non-empty string.")
        return ActionCandidate(
            action_type=intent,
            target_refs=(),
            metadata={"motivation": motivation},
            action_id=action_id,
            actor_id=actor_id,
            intent=intent,
            target=None,
            motivation=motivation,
        )
