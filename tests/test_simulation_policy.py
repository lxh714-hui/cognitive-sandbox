import pytest

from cognitive_sandbox.application.simulation_policy import SimulationPolicy
from cognitive_sandbox.domain.simulation import EventImportance, SimulationMode


@pytest.mark.parametrize(
    ("importance", "expected_mode"),
    [
        (EventImportance(0.2, "low"), SimulationMode.RULE_ONLY),
        (EventImportance(0.5, "medium"), SimulationMode.BASIC_COGNITION),
        (EventImportance(0.8, "high"), SimulationMode.FULL_COGNITION),
        (EventImportance(0.97, "high"), SimulationMode.DEEP_REASONING),
    ],
)
def test_policy_selects_mode_by_importance(importance, expected_mode):
    assert SimulationPolicy().select_mode(importance) is expected_mode


@pytest.mark.parametrize("mode", list(SimulationMode))
def test_all_modes_still_require_rule_simulation(mode):
    assert SimulationPolicy.should_run_rules(mode) is True


def test_policy_rejects_invalid_inputs():
    policy = SimulationPolicy()

    with pytest.raises(TypeError, match="EventImportance"):
        policy.select_mode(0.5)
    with pytest.raises(TypeError, match="SimulationMode"):
        policy.should_run_rules("rule_only")
