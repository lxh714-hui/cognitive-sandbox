from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.agent_context import AgentContext


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

    def __init__(self, *, action_id_factory: Callable[[], str] | None = None) -> None:
        self._action_id_factory = action_id_factory or (lambda: f"action_{uuid4().hex}")

    def generate(self, decision_input: ActionDecisionInput) -> tuple[ActionCandidate, ...]:
        if not isinstance(decision_input, ActionDecisionInput):
            raise TypeError("decision_input must be an ActionDecisionInput.")

        context = decision_input.agent_context
        situation = decision_input.situation.casefold()
        role = context.character_state.role.casefold()
        specific: tuple[str, str] | None = None
        if any(role_key in role for role_key in ("医生", "doctor", "physician")) and any(
            keyword in situation for keyword in ("受伤", "病人", "救助")
        ):
            specific = ("help", "compassion")
        elif any(role_key in role for role_key in ("士兵", "军人", "soldier")) and any(
            keyword in situation for keyword in ("危险", "攻击", "敌人")
        ):
            specific = ("protect", "duty")

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
