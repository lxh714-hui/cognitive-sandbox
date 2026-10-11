import pytest

from cognitive_sandbox.application.simulation_executor import SimulationExecutor
from cognitive_sandbox.domain.simulation import SimulationMode, SimulationStepResult
from cognitive_sandbox.domain.world_events import WorldEvent


def _event():
    return WorldEvent("event-1", "main", "harbor", "BREAK_OBJECT", "actor", {}, 2)


class _RecordingRuntime:
    def __init__(self, result=None):
        self.result = result or SimulationStepResult("event-1", (), ())
        self.calls = []

    def process_event(self, world_event, agent_ids, perception_contexts):
        self.calls.append((world_event, agent_ids, perception_contexts))
        return self.result


def test_rule_only_mode_returns_empty_result_without_agent_runtime():
    runtime = _RecordingRuntime()
    executor = SimulationExecutor(runtime)

    result = executor.execute(SimulationMode.RULE_ONLY, _event(), [], {})

    assert result == SimulationStepResult("event-1", (), ())
    assert runtime.calls == []


@pytest.mark.parametrize(
    "mode",
    [
        SimulationMode.BASIC_COGNITION,
        SimulationMode.FULL_COGNITION,
        SimulationMode.DEEP_REASONING,
    ],
)
def test_cognitive_modes_delegate_event_context_to_runtime(mode):
    runtime = _RecordingRuntime()
    executor = SimulationExecutor(runtime)
    agent_ids = ["agent-a"]
    contexts = {"agent-a": object()}

    result = executor.execute(mode, _event(), agent_ids, contexts)

    assert result.world_event_id == "event-1"
    assert runtime.calls == [(_event(), agent_ids, contexts)]


def test_executor_can_use_a_mode_specific_runtime():
    default_runtime = _RecordingRuntime()
    deep_runtime = _RecordingRuntime()
    executor = SimulationExecutor(
        default_runtime,
        mode_runtimes={SimulationMode.DEEP_REASONING: deep_runtime},
    )

    executor.execute(SimulationMode.DEEP_REASONING, _event(), [], {})

    assert deep_runtime.calls
    assert default_runtime.calls == []


def test_executor_rejects_invalid_mode_and_wrong_event_result():
    executor = SimulationExecutor(_RecordingRuntime())
    with pytest.raises(TypeError, match="SimulationMode"):
        executor.execute("full_cognition", _event(), [], {})

    wrong_result_runtime = _RecordingRuntime(SimulationStepResult("other-event", (), ()))
    with pytest.raises(ValueError, match="different world event"):
        SimulationExecutor(wrong_result_runtime).execute(
            SimulationMode.FULL_COGNITION,
            _event(),
            [],
            {},
        )


def test_mode_overrides_reject_rule_only_and_invalid_runtime():
    with pytest.raises(ValueError, match="Only cognitive"):
        SimulationExecutor(
            _RecordingRuntime(),
            mode_runtimes={SimulationMode.RULE_ONLY: _RecordingRuntime()},
        )
    with pytest.raises(TypeError, match="process_event"):
        SimulationExecutor(
            _RecordingRuntime(),
            mode_runtimes={SimulationMode.BASIC_COGNITION: object()},
        )
