from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.story_constraints import StoryConstraintEvaluator
from cognitive_sandbox.domain.story import HardConstraint, SoftConstraint, StoryObjective
from cognitive_sandbox.domain.world_events import WorldEvent


def _event(event_type="OBJECT_INSPECTED"):
    return WorldEvent("event-1", "main", "harbor", event_type, "agent-a", {}, 1)


def test_story_objective_is_immutable_and_validates_fields():
    objective = StoryObjective("obj-1", "Resolve the cup incident", 3)

    assert objective.priority == 3
    with pytest.raises(FrozenInstanceError):
        objective.priority = 4
    with pytest.raises(ValueError, match="priority"):
        StoryObjective("obj-1", "Resolve the cup incident", -1)
    with pytest.raises(ValueError, match="description"):
        StoryObjective("obj-1", " ", 1)


def test_hard_constraint_rejects_forbidden_event_type():
    constraint = HardConstraint(
        "no-death",
        "No character may die in this story.",
        forbidden_event_types=("CHARACTER_DIED",),
    )

    result = StoryConstraintEvaluator().evaluate(
        _event("CHARACTER_DIED"), hard_constraints=[constraint]
    )

    assert result.accepted is False
    assert result.hard_violations == ("no-death",)


def test_hard_constraint_allowed_types_pass_or_reject():
    constraint = HardConstraint(
        "investigation-only",
        "Keep this scene focused on investigation.",
        allowed_event_types=("OBJECT_INSPECTED", "CLUE_FOUND"),
    )
    evaluator = StoryConstraintEvaluator()

    accepted = evaluator.evaluate(_event(), hard_constraints=[constraint])
    rejected = evaluator.evaluate(_event("OBJECT_BROKEN"), hard_constraints=[constraint])

    assert accepted.accepted is True
    assert rejected.accepted is False
    assert rejected.hard_violations == ("investigation-only",)


def test_soft_constraints_compute_weighted_score_without_rejection():
    constraints = [
        SoftConstraint("prefer-inspection", "Prefer inspection scenes.", ("OBJECT_INSPECTED",), 0.75),
        SoftConstraint("prefer-clues", "Prefer clue discoveries.", ("CLUE_FOUND",), 0.25),
    ]

    result = StoryConstraintEvaluator().evaluate(
        _event(),
        soft_constraints=constraints,
    )

    assert result.accepted is True
    assert result.hard_violations == ()
    assert result.soft_score == pytest.approx(0.75)
    assert result.matched_soft_constraints == ("prefer-inspection",)


def test_no_soft_constraints_have_full_neutral_score():
    result = StoryConstraintEvaluator().evaluate(_event())

    assert result.accepted is True
    assert result.soft_score == 1.0


def test_constraints_require_unique_ids_and_valid_definitions():
    evaluator = StoryConstraintEvaluator()
    hard = HardConstraint("same-id", "Hard", forbidden_event_types=("BAD",))
    soft = SoftConstraint("same-id", "Soft", ("GOOD",))

    with pytest.raises(ValueError, match="unique"):
        evaluator.evaluate(_event(), hard_constraints=[hard], soft_constraints=[soft])
    with pytest.raises(ValueError, match="define allowed or forbidden"):
        HardConstraint("empty", "No rule")
    with pytest.raises(ValueError, match="cannot be both"):
        HardConstraint(
            "conflict",
            "Conflicting types",
            forbidden_event_types=("X",),
            allowed_event_types=("X",),
        )
