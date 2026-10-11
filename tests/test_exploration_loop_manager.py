from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.exploration_loop_manager import ExplorationLoopManager
from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.story import (
    BranchValue,
    ExplorationExecutionResult,
    ExplorationLoopPolicy,
    ExplorationLoopResult,
    StoryBranch,
)


class FakeController:
    def __init__(self):
        self.calls = []

    def plan(self, branch, branch_value, confidence, importance, **kwargs):
        self.calls.append((branch, branch_value, confidence, importance, kwargs))
        return object()


class FakeExecutor:
    def __init__(self, results):
        self.results = iter(results)
        self.calls = []

    def execute(self, plan, branch, candidates):
        self.calls.append((plan, branch, candidates))
        return next(self.results)


def make_manager(results):
    controller = FakeController()
    executor = FakeExecutor(results)
    return ExplorationLoopManager(controller, executor), controller, executor


def run(manager, policy):
    branch = StoryBranch("branch-1", None, "world", 0, None)
    return manager.run(
        branch,
        BranchValue("branch-1", 0.7, ()),
        0.4,
        0.8,
        (ActionCandidate("CONTINUE", ("next",), {}),),
        policy,
    )


def test_multiple_iterations_accumulate_execution_and_feedback_counts():
    manager, controller, executor = make_manager(
        (
            ExplorationExecutionResult("branch-1", True, 2, 3, 1),
            ExplorationExecutionResult("branch-1", True, 1, 3, 2),
            ExplorationExecutionResult("branch-1", True, 0, 3, 1),
        )
    )

    result = run(manager, ExplorationLoopPolicy(3, True))

    assert result == ExplorationLoopResult(3, 3, 4, "max_iterations_reached")
    assert len(controller.calls) == len(executor.calls) == 3


def test_loop_stops_at_maximum_iteration_limit():
    manager, _controller, executor = make_manager(
        ExplorationExecutionResult("branch-1", True, 0, 1, 1) for _ in range(4)
    )

    result = run(manager, ExplorationLoopPolicy(2, False))

    assert result.iterations == 2
    assert len(executor.calls) == 2
    assert result.stopped_reason == "max_iterations_reached"


def test_loop_stops_early_when_feedback_is_empty_and_policy_requests_it():
    manager, _controller, executor = make_manager(
        (
            ExplorationExecutionResult("branch-1", True, 1, 2, 1),
            ExplorationExecutionResult("branch-1", True, 1, 2, 0),
            ExplorationExecutionResult("branch-1", True, 1, 2, 1),
        )
    )

    result = run(manager, ExplorationLoopPolicy(5, True))

    assert result.iterations == 2
    assert result.executed_count == 2
    assert result.total_feedback_count == 1
    assert result.stopped_reason == "no_feedback"
    assert len(executor.calls) == 2


def test_loop_result_counts_unexecuted_plan_and_zero_iteration_case():
    manager, _controller, _executor = make_manager(
        (ExplorationExecutionResult("branch-1", False, 0, 0, 0),)
    )
    result = run(manager, ExplorationLoopPolicy(1, False))
    assert result.iterations == 1
    assert result.executed_count == 0

    empty = run(manager, ExplorationLoopPolicy(0, True))
    assert empty == ExplorationLoopResult(0, 0, 0, "max_iterations_reached")


def test_loop_policy_and_result_are_immutable_and_validate_counts():
    policy = ExplorationLoopPolicy(2, True)
    with pytest.raises(FrozenInstanceError):
        policy.max_iterations = 3
    with pytest.raises(ValueError, match="max_iterations"):
        ExplorationLoopPolicy(-1, False)

    result = ExplorationLoopResult(1, 1, 0, "no_feedback")
    with pytest.raises(FrozenInstanceError):
        result.iterations = 2
    with pytest.raises(ValueError, match="executed_count"):
        ExplorationLoopResult(1, 2, 0, "invalid")
