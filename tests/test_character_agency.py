from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.agency.character_agency import CharacterAgency


def test_character_agency_validates_ranges_and_is_immutable():
    agency = CharacterAgency("liuyiyi", .8, .7, .9, .2, "2030-01-01T00:00:00+00:00")
    assert agency.initiative == .8
    with pytest.raises(FrozenInstanceError):
        agency.initiative = .1
    with pytest.raises(ValueError):
        CharacterAgency("x", initiative=1.1)
