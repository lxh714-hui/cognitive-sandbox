from __future__ import annotations

from collections.abc import Callable
from typing import Protocol
from uuid import uuid4

from cognitive_sandbox.domain.story import (
    BranchSimulationRecord,
    StoryBranch,
    StorySimulationResult,
)


class BranchSimulationStore(Protocol):
    def create_branch_simulation(self, record: BranchSimulationRecord) -> None: ...
    def complete_branch_simulation(self, result: StorySimulationResult) -> BranchSimulationRecord: ...
    def get_branch_simulation(self, simulation_id: str) -> BranchSimulationRecord | None: ...
    def list_branch_simulations(self, branch_id: str) -> list[BranchSimulationRecord]: ...
    def get_branch_simulation_result(self, simulation_id: str) -> StorySimulationResult | None: ...


class BranchSimulationManager:
    """Create branch-scoped simulation records and associate their returned results."""

    def __init__(
        self,
        store: BranchSimulationStore,
        *,
        simulation_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._store = store
        self._simulation_id_factory = simulation_id_factory or (lambda: str(uuid4()))

    def create_task(self, branch: StoryBranch) -> BranchSimulationRecord:
        if not isinstance(branch, StoryBranch):
            raise TypeError("branch must be a StoryBranch.")
        record = BranchSimulationRecord(
            simulation_id=self._simulation_id_factory(),
            branch_id=branch.branch_id,
            result_status="pending",
        )
        self._store.create_branch_simulation(record)
        return record

    def associate_result(self, result: StorySimulationResult) -> BranchSimulationRecord:
        if not isinstance(result, StorySimulationResult):
            raise TypeError("result must be a StorySimulationResult.")
        record = self._store.get_branch_simulation(result.simulation_id)
        if record is None:
            raise LookupError(f"No branch simulation task found: {result.simulation_id}.")
        if record.result_status != "pending":
            raise ValueError("A result can only be associated with a pending task.")
        if any(event.branch_id != record.branch_id for event in result.events):
            raise ValueError("Simulation result contains events from a different branch.")
        return self._store.complete_branch_simulation(result)

    def history(self, branch_id: str) -> list[BranchSimulationRecord]:
        if not isinstance(branch_id, str) or not branch_id.strip():
            raise ValueError("branch_id must not be empty.")
        return self._store.list_branch_simulations(branch_id)

    def result(self, simulation_id: str) -> StorySimulationResult | None:
        if not isinstance(simulation_id, str) or not simulation_id.strip():
            raise ValueError("simulation_id must not be empty.")
        return self._store.get_branch_simulation_result(simulation_id)
