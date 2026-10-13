from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.encounter import EncounterCandidate, EncounterStatus, LocationCondition


def test_encounter_candidate_is_immutable_and_has_lifecycle_state():
    item = EncounterCandidate("a", "b", "market", "t0/t1", "paths overlap", .72,
                              (LocationCondition("market", "market", True),), EncounterStatus.AVAILABLE)
    assert item.status is EncounterStatus.AVAILABLE
    with pytest.raises(FrozenInstanceError):
        item.score = .1


def test_candidate_rejects_invalid_score_and_same_character():
    with pytest.raises(ValueError):
        EncounterCandidate("a", "b", "market", "t", "reason", 1.1)
    with pytest.raises(ValueError):
        EncounterCandidate("a", "a", "market", "t", "reason", .5)
