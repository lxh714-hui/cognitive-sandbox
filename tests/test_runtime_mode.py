from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.domain.runtime_mode import RuntimeMode, StorySimulationConfig


def test_runtime_modes_are_distinct_enum_values():
    assert RuntimeMode.ROLEPLAY.value == "roleplay"
    assert RuntimeMode.STORY_SIMULATION.value == "story_simulation"
    assert RuntimeMode.ROLEPLAY is not RuntimeMode.STORY_SIMULATION


def test_story_simulation_config_establishes_world_branch_and_initial_revision():
    config = StorySimulationConfig("harbor", "main", initial_world_revision=3)

    assert config.mode is RuntimeMode.STORY_SIMULATION
    assert config.world_id == "harbor"
    assert config.branch_id == "main"
    assert config.initial_world_revision == 3


def test_story_simulation_config_is_immutable():
    config = StorySimulationConfig("harbor", "main")

    with pytest.raises(FrozenInstanceError):
        config.world_id = "elsewhere"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"world_id": " ", "branch_id": "main"},
        {"world_id": "harbor", "branch_id": " "},
    ],
)
def test_story_simulation_config_requires_world_and_branch(kwargs):
    with pytest.raises(ValueError):
        StorySimulationConfig(**kwargs)


@pytest.mark.parametrize("revision", [-1, True, 1.5])
def test_story_simulation_config_validates_initial_revision(revision):
    with pytest.raises((TypeError, ValueError)):
        StorySimulationConfig("harbor", "main", initial_world_revision=revision)
