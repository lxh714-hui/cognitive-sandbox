from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from cognitive_sandbox.domain.actions import (
    ActionCandidate,
    ActionProposal,
    ResolvedAction,
    ResolvedActionResult,
)


class ActionResolver:
    """Resolve action candidates or arbitrate world action proposals.

    Candidate resolution produces descriptive feedback only. Proposal resolution
    retains the existing revision and priority arbitration behavior.
    """

    _OUTCOMES = {
        "help": (True, "角色尝试提供帮助", {"social": "positive"}),
        "protect": (True, "角色尝试保护目标", {"safety": "increased"}),
        "observe": (True, "角色观察周围环境", {"information": "gained"}),
    }

    def resolve(
        self,
        actions: Iterable[ActionProposal] | ActionCandidate,
        world_state: Mapping[str, Any] | None = None,
        *,
        current_world_revision: int | None = None,
    ) -> list[ResolvedAction] | ResolvedActionResult:
        if isinstance(actions, ActionCandidate):
            if current_world_revision is not None:
                raise TypeError("current_world_revision applies only to proposal resolution.")
            return self.resolve_candidate(actions, world_state)
        if world_state is not None:
            raise TypeError("action must be an ActionCandidate when world_state is supplied.")
        return self._resolve_proposals(actions, current_world_revision)

    def resolve_candidate(
        self,
        action: ActionCandidate,
        world_state: Mapping[str, Any] | None,
    ) -> ResolvedActionResult:
        if not isinstance(action, ActionCandidate):
            raise TypeError("action must be an ActionCandidate.")
        if not isinstance(world_state, Mapping):
            raise TypeError("world_state must be a mapping.")

        outcome = self._OUTCOMES.get(action.intent)
        if outcome is None:
            success, description, impact = (
                False,
                "行动无法解析",
                {"error": "unknown_action"},
            )
        else:
            success, description, impact = outcome
        return ResolvedActionResult(
            action_id=action.action_id,
            success=success,
            event_description=description,
            impact=impact,
        )

    @staticmethod
    def _resolve_proposals(
        proposals: Iterable[ActionProposal],
        current_world_revision: int | None,
    ) -> list[ResolvedAction]:
        if isinstance(current_world_revision, bool) or not isinstance(current_world_revision, int):
            raise TypeError("current_world_revision must be an integer.")
        if current_world_revision < 0:
            raise ValueError("current_world_revision must be non-negative.")
        if isinstance(proposals, (str, bytes)):
            raise TypeError("proposals must be an iterable of ActionProposal values.")

        actions = tuple(proposals)
        if any(not isinstance(action, ActionProposal) for action in actions):
            raise TypeError("proposals must contain only ActionProposal values.")

        # Deterministic tie-breaks keep the result stable regardless of input order.
        ordered = sorted(
            actions,
            key=lambda action: (-action.priority, action.actor_id, action.proposal_id),
        )
        accepted_actors: set[str] = set()
        resolved: list[ResolvedAction] = []
        for action in ordered:
            if action.base_world_revision != current_world_revision:
                resolved.append(
                    ResolvedAction(
                        action,
                        False,
                        "Proposal world revision does not match the current revision.",
                    )
                )
            elif action.actor_id in accepted_actors:
                resolved.append(
                    ResolvedAction(
                        action,
                        False,
                        "A higher-priority proposal from this agent was already accepted.",
                    )
                )
            else:
                accepted_actors.add(action.actor_id)
                resolved.append(
                    ResolvedAction(action, True, "Accepted by priority and revision rules.")
                )
        return resolved
