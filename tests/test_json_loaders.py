from __future__ import annotations

import json

import pytest

from cognitive_sandbox.application.json_character_loader import JsonCharacterLoader
from cognitive_sandbox.application.json_event_loader import JsonEventLoader
from cognitive_sandbox.application.json_world_loader import JsonWorldLoader
from cognitive_sandbox.domain.validation_result import ValidationResult


def _write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def test_json_loaders_create_domain_objects_from_valid_files(tmp_path):
    world_path = _write_json(
        tmp_path / "world.json",
        {
            "world_id": "harbor",
            "name": "末日城市",
            "description": "灾难后的城市",
            "history": ["灾难爆发"],
            "rules": ["感染不可逆"],
        },
    )
    character_path = _write_json(
        tmp_path / "character.json",
        {
            "character_id": "doctor",
            "name": "林夏",
            "identity": {"age": 29, "gender": "女", "occupation": "医生"},
            "personality": ["谨慎"],
            "background": "灾难前在医院工作。",
            "goals": ["救助患者"],
            "constraints": [{"type": "hard", "content": "不会伤害无辜者"}],
        },
    )
    event_path = _write_json(
        tmp_path / "event.json",
        {
            "event_id": "power_failure",
            "name": "医院停电",
            "description": "备用电源即将耗尽",
            "event_type": "initial",
            "participants": ["doctor"],
            "conditions": ["night"],
            "effects": ["hospital_dark"],
            "priority": 2,
        },
    )

    world = JsonWorldLoader().load(world_path)
    character = JsonCharacterLoader().load(character_path)
    event = JsonEventLoader().load(event_path)

    assert world.history == ("灾难爆发",)
    assert world.rules == ("感染不可逆",)
    assert character.character_id == "doctor"
    assert character.age == 29
    assert character.constraints[0].type == "hard"
    assert event.participants == ("doctor",)
    assert event.priority == 2


@pytest.mark.parametrize(
    ("loader_type", "document", "expected_error"),
    [
        (
            JsonWorldLoader,
            {"world_id": "w", "name": "name", "description": "desc", "history": [], "rules": [], "extra": 1},
            "unexpected fields",
        ),
        (
            JsonCharacterLoader,
            {
                "character_id": "c", "name": "name", "identity": {}, "personality": [],
                "background": "", "goals": [], "constraints": [{"type": "invalid", "content": "x"}],
            },
            "invalid constraints",
        ),
        (
            JsonEventLoader,
            {
                "event_id": "e", "name": "name", "description": "desc", "event_type": "initial",
                "participants": [], "conditions": [], "effects": [], "priority": -1,
            },
            "priority",
        ),
    ],
)
def test_json_loaders_reject_invalid_schema_or_domain_values(
    tmp_path, loader_type, document, expected_error
):
    path = _write_json(tmp_path / "input.json", document)

    with pytest.raises(ValueError, match=expected_error):
        loader_type().load(path)


def test_json_loader_rejects_validator_failure(tmp_path):
    class RejectingValidator:
        def validate(self, _document):
            return ValidationResult(False, ("blocked by validator",), ())

    path = _write_json(
        tmp_path / "world.json",
        {"world_id": "w", "name": "name", "description": "desc", "history": [], "rules": []},
    )

    with pytest.raises(ValueError, match="blocked by validator"):
        JsonWorldLoader(RejectingValidator()).load(path)


def test_json_loader_reports_malformed_json_clearly(tmp_path):
    path = tmp_path / "world.json"
    path.write_text("{broken", encoding="utf-8")

    with pytest.raises(ValueError, match="could not read world JSON"):
        JsonWorldLoader().load(path)
