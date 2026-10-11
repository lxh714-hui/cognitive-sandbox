from cognitive_sandbox.application.world_validator import WorldValidator
from cognitive_sandbox.domain.world_document import WorldDocument


def test_world_validator_accepts_valid_document():
    result = WorldValidator().validate(
        WorldDocument("world", "末日城市", "灾难后的城市", history=("灾难爆发",), rules=("感染不可逆",))
    )

    assert result.valid
    assert result.errors == ()


def test_world_validator_rejects_empty_required_fields_and_invalid_rules():
    document = object.__new__(WorldDocument)
    object.__setattr__(document, "world_id", "")
    object.__setattr__(document, "name", "")
    object.__setattr__(document, "description", "城市")
    object.__setattr__(document, "history", ["灾难爆发"])
    object.__setattr__(document, "rules", ("",))

    result = WorldValidator().validate(document)

    assert not result.valid
    assert any("world_id" in error for error in result.errors)
    assert any("name" in error for error in result.errors)
    assert any("history" in error for error in result.errors)
    assert any("rules" in error for error in result.errors)
    assert document.history == ["灾难爆发"]
