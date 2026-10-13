from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from cognitive_sandbox.application.character_card_validator import CharacterCardValidator
from cognitive_sandbox.application.event_card_validator import EventCardValidator
from cognitive_sandbox.application.scenario_validator import ScenarioValidator
from cognitive_sandbox.application.world_validator import WorldValidator
from cognitive_sandbox.domain.scenario_content import ScenarioContent
from cognitive_sandbox.domain.validation_result import ValidationResult
from cognitive_sandbox.domain.world_document import WorldDocument


class ScenarioExporter:
    """Serialize validated immutable content into a directory package."""

    def __init__(self) -> None:
        self._scenario_validator = ScenarioValidator()
        self._world_validator = WorldValidator()
        self._character_validator = CharacterCardValidator()
        self._event_validator = EventCardValidator()

    def export(self, content: ScenarioContent, directory: str | Path) -> Path:
        self._validate(content)
        root = Path(directory)
        root.mkdir(parents=True, exist_ok=True)
        (root / "characters").mkdir(exist_ok=True)
        (root / "events").mkdir(exist_ok=True)

        self._write_json(
            root / "scenario.json",
            {
                "scenario_id": content.scenario.scenario_id,
                "name": content.scenario.name,
                "description": content.scenario.description,
                "initial_world_state": _json_value(content.scenario.initial_world_state),
                "character_templates": _json_value(content.scenario.character_templates),
            },
        )
        document = content.world_document
        self._write_json(
            root / "world.json",
            {
                "world_id": document.world_id,
                "name": document.name,
                "description": document.description,
                "history": list(document.history),
                "rules": list(document.rules),
            },
        )
        for index, card in enumerate(content.character_cards):
            identity = {
                "age": card.age,
                "gender": card.gender,
                "occupation": card.occupation,
            }
            if card.portrait is not None:
                identity["portrait"] = card.portrait
            self._write_json(
                root / "characters" / f"character_{index:04d}.json",
                {
                    "character_id": card.character_id,
                    "name": card.name,
                    "identity": identity,
                    "personality": list(card.personality),
                    "background": card.background,
                    "goals": list(card.goals),
                    "constraints": [
                        {"type": constraint.type, "content": constraint.content}
                        for constraint in card.constraints
                    ],
                    "example_dialogues": [
                        {"user": example.user, "character": example.character}
                        for example in card.example_dialogues
                    ],
                    "identity_editable": card.identity_editable,
                },
            )
        for index, card in enumerate(content.event_cards):
            self._write_json(
                root / "events" / f"event_{index:04d}.json",
                {
                    "event_id": card.event_id,
                    "name": card.name,
                    "description": card.description,
                    "event_type": card.event_type,
                    "participants": list(card.participants),
                    "conditions": list(card.conditions),
                    "effects": list(card.effects),
                    "priority": card.priority,
                },
            )
        return root

    def _validate(self, content: ScenarioContent) -> None:
        if not isinstance(content, ScenarioContent):
            raise TypeError("content must be a ScenarioContent.")
        if content.world_document is None:
            raise ValueError("scenario content validation failed: world_document is required")
        results: list[tuple[str, ValidationResult]] = [
            ("scenario", self._scenario_validator.validate(content.scenario)),
            ("world_document", self._world_validator.validate(content.world_document)),
        ]
        results.extend(
            (f"character_cards[{index}]", self._character_validator.validate(card))
            for index, card in enumerate(content.character_cards)
        )
        results.extend(
            (f"event_cards[{index}]", self._event_validator.validate(card))
            for index, card in enumerate(content.event_cards)
        )
        errors = [f"{label}: {error}" for label, result in results for error in result.errors]
        if errors:
            raise ValueError("scenario content validation failed: " + "; ".join(errors))

    @staticmethod
    def _write_json(path: Path, value: Mapping[str, Any]) -> None:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [_json_value(item) for item in sorted(value, key=repr)]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"value of type {type(value).__name__} is not JSON serializable")
