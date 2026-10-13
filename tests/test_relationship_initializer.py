from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.relationship_initializer import RelationshipInitializer
from cognitive_sandbox.domain.relationship import RelationshipState


def test_scenario_relationships_are_copied_without_role_inference():
    relationships = RelationshipInitializer().initialize(
        "角色", source_id="character-1",
        relationships=({"target_id": "person-2", "relation_type": "care", "trust": .6},),
    )

    assert relationships == (RelationshipState("character-1", "person-2", "care", 0.6),)


def test_role_without_configured_relationships_starts_unconnected():
    relationships = RelationshipInitializer().initialize("角色", source_id="character-1")

    assert relationships == ()


def test_unknown_role_has_no_initial_relationships():
    assert RelationshipInitializer().initialize("园丁") == ()


def test_relationship_state_is_immutable_and_validates_trust():
    relation = RelationshipState("a", "b", "friend", 0.5)
    with pytest.raises(FrozenInstanceError):
        relation.trust = 0.9
    with pytest.raises(ValueError, match="trust"):
        RelationshipState("a", "b", "friend", 1.1)

