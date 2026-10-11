from __future__ import annotations

from collections.abc import Iterable

from cognitive_sandbox.domain.story import (
    ConstraintEvaluation,
    HardConstraint,
    SoftConstraint,
)
from cognitive_sandbox.domain.world_events import WorldEvent


class StoryConstraintEvaluator:
    """Evaluate declarative hard and soft story constraints for one world event."""

    def evaluate(
        self,
        world_event: WorldEvent,
        *,
        hard_constraints: Iterable[HardConstraint] = (),
        soft_constraints: Iterable[SoftConstraint] = (),
    ) -> ConstraintEvaluation:
        if not isinstance(world_event, WorldEvent):
            raise TypeError("world_event must be a WorldEvent.")
        hard = tuple(hard_constraints)
        soft = tuple(soft_constraints)
        if any(not isinstance(item, HardConstraint) for item in hard):
            raise TypeError("hard_constraints must contain HardConstraint values.")
        if any(not isinstance(item, SoftConstraint) for item in soft):
            raise TypeError("soft_constraints must contain SoftConstraint values.")
        all_ids = [item.constraint_id for item in (*hard, *soft)]
        if len(set(all_ids)) != len(all_ids):
            raise ValueError("Constraint IDs must be unique within an evaluation.")

        violations: list[str] = []
        for constraint in hard:
            if constraint.forbidden_event_types and world_event.event_type in constraint.forbidden_event_types:
                violations.append(constraint.constraint_id)
            elif (
                constraint.allowed_event_types
                and world_event.event_type not in constraint.allowed_event_types
            ):
                violations.append(constraint.constraint_id)

        matched_soft = tuple(
            constraint.constraint_id
            for constraint in soft
            if world_event.event_type in constraint.preferred_event_types
        )
        total_weight = sum(constraint.weight for constraint in soft)
        matched_weight = sum(
            constraint.weight
            for constraint in soft
            if constraint.constraint_id in matched_soft
        )
        soft_score = matched_weight / total_weight if total_weight else 1.0
        return ConstraintEvaluation(
            world_event_id=world_event.event_id,
            accepted=not violations,
            hard_violations=tuple(violations),
            soft_score=soft_score,
            matched_soft_constraints=matched_soft,
        )

    def evaluate_events(
        self,
        world_events: Iterable[WorldEvent],
        *,
        hard_constraints: Iterable[HardConstraint] = (),
        soft_constraints: Iterable[SoftConstraint] = (),
    ) -> ConstraintEvaluation:
        """Aggregate constraint outcomes over an ordered story event stream."""
        events = tuple(world_events)
        if not events:
            raise ValueError("world_events must contain at least one event.")
        hard = tuple(hard_constraints)
        soft = tuple(soft_constraints)
        evaluations = [
            self.evaluate(
                event,
                hard_constraints=hard,
                soft_constraints=soft,
            )
            for event in events
        ]
        violations = tuple(
            f"{evaluation.world_event_id}:{constraint_id}"
            for evaluation in evaluations
            for constraint_id in evaluation.hard_violations
        )
        matched = tuple(
            dict.fromkeys(
                f"{evaluation.world_event_id}:{constraint_id}"
                for evaluation in evaluations
                for constraint_id in evaluation.matched_soft_constraints
            )
        )
        score = sum(evaluation.soft_score for evaluation in evaluations) / len(evaluations)
        return ConstraintEvaluation(
            world_event_id=events[0].event_id,
            accepted=not violations,
            hard_violations=violations,
            soft_score=score,
            matched_soft_constraints=matched,
            source_event_ids=tuple(event.event_id for event in events),
        )
