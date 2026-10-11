from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.relationship_initializer import RelationshipInitializer
from cognitive_sandbox.domain.relationship import RelationshipState


def test_doctor_gets_care_relationship_with_patient():
    relationships = RelationshipInitializer().initialize("年轻医生", source_id="doctor-1")

    assert relationships == (RelationshipState("doctor-1", "patient", "care", 0.6),)


def test_soldier_gets_comrade_relationship():
    relationships = RelationshipInitializer().initialize("士兵", source_id="soldier-1")

    assert relationships == (RelationshipState("soldier-1", "comrade", "comrade", 0.8),)


def test_unknown_role_has_no_initial_relationships():
    assert RelationshipInitializer().initialize("园丁") == ()


def test_relationship_state_is_immutable_and_validates_trust():
    relation = RelationshipState("a", "b", "friend", 0.5)
    with pytest.raises(FrozenInstanceError):
        relation.trust = 0.9
    with pytest.raises(ValueError, match="trust"):
        RelationshipState("a", "b", "friend", 1.1)

