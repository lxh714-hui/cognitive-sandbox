from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.domain.story import StoryBranch


def test_story_branch_models_root_and_sibling_routes():
    root = StoryBranch("main", None, "harbor", 3, None)
    route_a = StoryBranch("route-a", root.branch_id, "harbor", 4, "event-a")
    route_b = StoryBranch("route-b", root.branch_id, "harbor", 4, "event-b")

    assert route_a.parent_branch_id == route_b.parent_branch_id == root.branch_id
    assert route_a.branch_id != route_b.branch_id
    assert route_a.divergence_event_id != route_b.divergence_event_id


def test_story_branch_is_immutable():
    branch = StoryBranch("main", None, "harbor", 0, None)

    with pytest.raises(FrozenInstanceError):
        branch.revision = 1


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch_id": " ", "parent_branch_id": None, "world_id": "harbor", "revision": 0,
         "divergence_event_id": None},
        {"branch_id": "main", "parent_branch_id": "main", "world_id": "harbor", "revision": 0,
         "divergence_event_id": None},
        {"branch_id": "main", "parent_branch_id": None, "world_id": "harbor", "revision": -1,
         "divergence_event_id": None},
        {"branch_id": "main", "parent_branch_id": None, "world_id": "harbor", "revision": 0,
         "divergence_event_id": " "},
    ],
)
def test_story_branch_rejects_invalid_fields(kwargs):
    with pytest.raises((TypeError, ValueError)):
        StoryBranch(**kwargs)
