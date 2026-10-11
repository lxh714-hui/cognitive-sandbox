from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.rollout_manager import RolloutManager
from cognitive_sandbox.domain.story import RolloutAllocation, RolloutPolicy


@pytest.fixture
def manager():
    return RolloutManager(RolloutPolicy(min_rollouts=0, max_rollouts=20))


def test_high_value_low_confidence_receives_more_rollouts(manager):
    uncertain = manager.rollout_count(branch_value=0.9, confidence=0.1, importance=0.5)
    certain = manager.rollout_count(branch_value=0.9, confidence=0.9, importance=0.5)

    assert uncertain > certain


def test_high_confidence_reduces_rollout_count(manager):
    low_confidence = manager.rollout_count(0.6, 0.2, 0.5)
    high_confidence = manager.rollout_count(0.6, 0.9, 0.5)

    assert high_confidence < low_confidence


def test_high_importance_increases_rollout_count(manager):
    ordinary = manager.rollout_count(0.6, 0.4, 0.5)
    important = manager.rollout_count(0.6, 0.4, 0.8)

    assert important > ordinary


def test_low_importance_reduces_rollout_count(manager):
    ordinary = manager.rollout_count(0.6, 0.4, 0.5)
    unimportant = manager.rollout_count(0.6, 0.4, 0.2)

    assert unimportant < ordinary


def test_rollout_count_stays_within_policy_bounds():
    manager = RolloutManager(RolloutPolicy(min_rollouts=3, max_rollouts=7))

    assert manager.rollout_count(0.0, 1.0, 0.0) == 3
    assert manager.rollout_count(1.0, 0.0, 1.0) == 7


def test_policy_validates_bounds_and_is_immutable():
    with pytest.raises(ValueError, match="min_rollouts"):
        RolloutPolicy(4, 3)
    with pytest.raises(ValueError, match="non-negative"):
        RolloutPolicy(-1, 3)
    with pytest.raises(TypeError, match="integer"):
        RolloutPolicy(1.5, 3)

    policy = RolloutPolicy(1, 3)
    with pytest.raises(FrozenInstanceError):
        policy.min_rollouts = 2


def test_allocation_model_validates_and_is_immutable():
    allocation = RolloutAllocation("branch-1", 2, "uncertain high-value branch")
    assert allocation.rollout_count == 2
    with pytest.raises(FrozenInstanceError):
        allocation.rollout_count = 1
    with pytest.raises(ValueError, match="branch_id"):
        RolloutAllocation(" ", 2, "reason")


@pytest.mark.parametrize("importance", [-0.1, 1.1])
def test_importance_must_be_in_range(manager, importance):
    with pytest.raises(ValueError, match="importance"):
        manager.rollout_count(0.5, 0.5, importance)
