from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.world_document_loader import WorldDocumentLoader
from cognitive_sandbox.application.world_validator import WorldValidator
from cognitive_sandbox.domain.world_document import WorldDocument


def test_world_document_creation_and_immutable_collections():
    history = ["三年前灾难爆发"]
    rules = ["感染不可逆"]
    document = WorldDocument("example", "末日城市", "灾难后的城市", history, rules)

    history.append("后来发生了新事")
    rules.clear()
    assert document.history == ("三年前灾难爆发",)
    assert document.rules == ("感染不可逆",)
    assert isinstance(document.history, tuple)
    with pytest.raises(FrozenInstanceError):
        document.name = "其他世界"


def test_world_document_rejects_invalid_fields_and_rule_formats():
    with pytest.raises(ValueError, match="world_id"):
        WorldDocument(" ", "name", "description")
    with pytest.raises(ValueError, match="rules"):
        WorldDocument("world", "name", "description", rules=("",))
    with pytest.raises(TypeError, match="history"):
        WorldDocument("world", "name", "description", history="not-a-tuple")


def test_world_validator_and_in_memory_loader_preserve_document():
    document = WorldDocument("example", "末日城市", "灾难后的城市", ("灾难爆发",), ("感染不可逆",))
    before = (document.world_id, document.name, document.description, document.history, document.rules)
    validator = WorldValidator()
    loader = WorldDocumentLoader((document,))

    assert validator.validate(document).valid
    assert loader.load("example") is document
    assert loader.load("missing") is None
    assert (document.world_id, document.name, document.description, document.history, document.rules) == before


def test_world_validator_reports_malformed_rule_tuple_without_mutating_input():
    document = object.__new__(WorldDocument)
    object.__setattr__(document, "world_id", "example")
    object.__setattr__(document, "name", "末日城市")
    object.__setattr__(document, "description", "灾难后的城市")
    object.__setattr__(document, "history", ("灾难爆发",))
    object.__setattr__(document, "rules", ("",))

    result = WorldValidator().validate(document)

    assert not result.valid
    assert any("rules" in error for error in result.errors)
    assert document.rules == ("",)
