from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.exploration_executor import ExplorationExecutor
from cognitive_sandbox.application.lazy_expander import LazyExpander
from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.story import (
    ExplorationExecutionResult,
    ExplorationPlan,
    ExpansionPolicy,
    PruningDecision,
    RolloutAllocation,
    StoryBranch,
)


class FakeSimulationExecutor:
    def __init__(self, feedback=()):
        self.feedback = feedback
        self.calls = []

    def execute_rollouts(self, branch, rollout_count):
        self.calls.append((branch, rollout_count))
        return self.feedback


class FakeLazyExpander:
    def __init__(self, expanded):
        self.expanded = expanded
        self.calls = []

    def expand(self, branch, candidates, policy):
        self.calls.append((branch, tuple(candidates), policy))
        return self.expanded


def make_plan(*, should_explore=True, expansion_policy=None, rollout_count=3):
    branch_id = "branch-1"
    return ExplorationPlan(
        branch_id=branch_id,
        should_explore=should_explore,
        priority=0.8 if should_explore else 0,
        expansion_policy=expansion_policy or ExpansionPolicy(2, 5),
        rollout_allocation=RolloutAllocation(branch_id, rollout_count, "test allocation"),
        pruning_decision=PruningDecision(branch_id, should_explore, "test decision"),
    )


def test_pruned_plan_skips_expansion_and_simulation():
    expander = FakeLazyExpander(())
    simulator = FakeSimulationExecutor(("feedback",))
    executor = ExplorationExecutor(expander, simulator)
    branch = StoryBranch("branch-1", None, "world", 0, None)

    result = executor.execute(make_plan(should_explore=False), branch, ())

    assert result == ExplorationExecutionResult("branch-1", False, 0, 0, 0)
    assert expander.calls == []
    assert simulator.calls == []


def test_approved_plan_expands_and_passes_rollout_count_to_simulator():
    branch = StoryBranch("branch-1", None, "world", 0, None)
    children = (
        StoryBranch("child-1", "branch-1", "world", 0, None),
        StoryBranch("child-2", "branch-1", "world", 0, None),
    )
    expander = FakeLazyExpander(children)
    simulator = FakeSimulationExecutor(("feedback-1", "feedback-2"))
    executor = ExplorationExecutor(expander, simulator)
    candidates = (ActionCandidate("CONTINUE", ("next",), {}),)
    policy = ExpansionPolicy(2, 5)

    result = executor.execute(
        make_plan(expansion_policy=policy, rollout_count=4), branch, candidates
    )

    assert expander.calls == [(branch, candidates, policy)]
    assert simulator.calls == [(branch, 4)]
    assert result.executed
    assert result.expanded_count == 2
    assert result.rollout_count == 4
    assert result.feedback_count == 2


def test_zero_rollout_allocation_skips_simulation_call():
    branch = StoryBranch("branch-1", None, "world", 0, None)
    simulator = FakeSimulationExecutor()
    executor = ExplorationExecutor(FakeLazyExpander(()), simulator)

    result = executor.execute(make_plan(rollout_count=0), branch, ())

    assert result.executed
    assert result.rollout_count == 0
    assert simulator.calls == []


def test_execution_result_is_immutable_and_validates_counts():
    result = ExplorationExecutionResult("branch-1", True, 1, 2, 1)
    with pytest.raises(FrozenInstanceError):
        result.feedback_count = 0
    with pytest.raises(ValueError, match="non-negative"):
        ExplorationExecutionResult("branch-1", True, -1, 0, 0)


def test_executor_rejects_plan_for_another_branch():
    executor = ExplorationExecutor(FakeLazyExpander(()), FakeSimulationExecutor())
    branch = StoryBranch("different", None, "world", 0, None)

    with pytest.raises(ValueError, match="IDs must match"):
        executor.execute(make_plan(), branch, ())
