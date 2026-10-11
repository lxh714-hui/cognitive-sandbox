import pytest

from cognitive_sandbox.application.search_priority import SearchPriorityCalculator
from cognitive_sandbox.domain.story import BranchValue


def test_lower_confidence_adds_exploration_priority():
    calculator = SearchPriorityCalculator()
    value = BranchValue("branch", 0.8, ())

    assert calculator.calculate(value, 0.0) == pytest.approx(1.0)
    assert calculator.calculate(value, 0.0) > calculator.calculate(value, 1.0)


def test_high_confidence_has_no_exploration_bonus():
    assert SearchPriorityCalculator().calculate(0.7, 1.0) == pytest.approx(0.7)


@pytest.mark.parametrize(
    ("value", "confidence", "expected"),
    [(0.0, 1.0, 0.0), (0.0, 0.0, 0.2), (1.0, 0.0, 1.2), (1.0, 1.0, 1.0)],
)
def test_priority_is_bounded_for_boundary_values(value, confidence, expected):
    priority = SearchPriorityCalculator().calculate(value, confidence)
    assert priority == pytest.approx(expected)
    assert 0.0 <= priority <= 1.2


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_confidence_must_be_in_range(confidence):
    with pytest.raises(ValueError, match="confidence"):
        SearchPriorityCalculator().calculate(0.5, confidence)
