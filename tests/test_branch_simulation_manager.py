import pytest
from dataclasses import FrozenInstanceError

from cognitive_sandbox.application.branch_simulation_manager import BranchSimulationManager
from cognitive_sandbox.domain.story import (
    BranchSimulationRecord,
    ConstraintEvaluation,
    StoryBranch,
    StorySimulationResult,
)
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.infrastructure.sqlite_store import SQLiteEventStore


def _branch(branch_id="branch-a"):
    return StoryBranch(branch_id, "main", "harbor", 1, "divergence-event")


def _result(simulation_id, branch_id="branch-a", *, success=True):
    event = WorldEvent("event-1", branch_id, "harbor", "CLUE_FOUND", "agent-a", {"clue": "x"}, 2)
    evaluation = ConstraintEvaluation(
        "event-1",
        success,
        () if success else ("constraint-failed",),
        0.8,
        (),
        ("event-1",),
    )
    return StorySimulationResult(simulation_id, success, 1, (event,), evaluation)


def test_branch_simulation_record_is_immutable_and_validates_status():
    record = BranchSimulationRecord("sim-1", "branch-a", "pending")

    with pytest.raises(FrozenInstanceError):
        record.result_status = "succeeded"
    with pytest.raises(ValueError, match="result_status"):
        BranchSimulationRecord("sim-2", "branch-a", "unknown")


def test_manager_creates_pending_task_and_queries_branch_history(tmp_path):
    store = SQLiteEventStore(tmp_path / "branch-history.sqlite3")
    manager = BranchSimulationManager(store, simulation_id_factory=lambda: "sim-1")

    record = manager.create_task(_branch())

    assert record == BranchSimulationRecord("sim-1", "branch-a", "pending")
    assert manager.history("branch-a") == [record]
    assert manager.result("sim-1") is None


def test_manager_associates_and_restores_result(tmp_path):
    store = SQLiteEventStore(tmp_path / "branch-result.sqlite3")
    manager = BranchSimulationManager(store, simulation_id_factory=lambda: "sim-1")
    manager.create_task(_branch())

    result = _result("sim-1")
    completed = manager.associate_result(result)

    assert completed.result_status == "succeeded"
    assert manager.history("branch-a") == [completed]
    assert manager.result("sim-1") == result


def test_manager_records_failed_simulation_and_keeps_branch_histories_isolated(tmp_path):
    store = SQLiteEventStore(tmp_path / "branch-isolation.sqlite3")
    ids = iter(["sim-a", "sim-b"])
    manager = BranchSimulationManager(store, simulation_id_factory=lambda: next(ids))
    manager.create_task(_branch("branch-a"))
    manager.create_task(_branch("branch-b"))

    failed = manager.associate_result(_result("sim-b", "branch-b", success=False))

    assert failed.result_status == "failed"
    assert [item.simulation_id for item in manager.history("branch-a")] == ["sim-a"]
    assert manager.history("branch-b") == [failed]


def test_manager_rejects_unknown_completed_and_wrong_branch_results(tmp_path):
    store = SQLiteEventStore(tmp_path / "branch-validation.sqlite3")
    manager = BranchSimulationManager(store, simulation_id_factory=lambda: "sim-1")
    manager.create_task(_branch())

    with pytest.raises(ValueError, match="different branch"):
        manager.associate_result(_result("sim-1", "branch-b"))
    with pytest.raises(LookupError, match="task found"):
        manager.associate_result(_result("unknown"))

    manager.associate_result(_result("sim-1"))
    with pytest.raises(ValueError, match="pending task"):
        manager.associate_result(_result("sim-1"))
