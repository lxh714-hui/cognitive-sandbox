from __future__ import annotations

from collections.abc import Iterable

from cognitive_sandbox.domain.actions import ActionProposal, ResolvedAction


class ActionResolver:
    """Deterministically arbitrate proposals without executing or persisting them."""

    def resolve(
        self,
        proposals: Iterable[ActionProposal],
        *,
        current_world_revision: int,
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
