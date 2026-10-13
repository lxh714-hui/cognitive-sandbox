from __future__ import annotations

from pathlib import Path
from cognitive_sandbox.application.character_card_validator import CharacterCardValidator
from cognitive_sandbox.application.json_world_loader import _read_json_object, _require_fields
from cognitive_sandbox.domain.character_card import CharacterCard, ExampleDialogue
from cognitive_sandbox.domain.constraint import Constraint


class JsonCharacterLoader:
    REQUIRED_FIELDS = frozenset(
        {"character_id", "name", "identity", "personality", "background", "goals", "constraints"}
    )
    IDENTITY_FIELDS = frozenset({"age", "gender", "occupation", "portrait"})

    def __init__(self, validator: CharacterCardValidator | None = None) -> None:
        self._validator = validator or CharacterCardValidator()

    def load(self, path: str | Path) -> CharacterCard:
        data = _read_json_object(path, "character")
        missing = sorted(self.REQUIRED_FIELDS - data.keys())
        unexpected = sorted(data.keys() - self.REQUIRED_FIELDS - {"example_dialogues", "identity_editable"})
        if missing or unexpected:
            details = []
            if missing:
                details.append("missing fields: " + ", ".join(missing))
            if unexpected:
                details.append("unexpected fields: " + ", ".join(unexpected))
            raise ValueError("invalid character JSON schema (" + "; ".join(details) + ")")
        identity = data["identity"]
        if not isinstance(identity, dict):
            raise ValueError("invalid character JSON schema (identity must be an object)")
        unexpected_identity = sorted(identity.keys() - self.IDENTITY_FIELDS)
        if unexpected_identity:
            raise ValueError(
                "invalid character JSON schema (unexpected identity fields: "
                + ", ".join(unexpected_identity)
                + ")"
            )
        raw_constraints = data["constraints"]
        if not isinstance(raw_constraints, list):
            raise ValueError("invalid character JSON schema (constraints must be an array)")
        constraints: list[Constraint] = []
        for index, raw_constraint in enumerate(raw_constraints):
            if not isinstance(raw_constraint, dict):
                raise ValueError(f"constraints[{index}] must be an object")
            _require_fields(raw_constraint, frozenset({"type", "content"}), f"constraints[{index}]")
            try:
                constraints.append(Constraint(raw_constraint["type"], raw_constraint["content"]))
            except (TypeError, ValueError) as error:
                raise ValueError(f"invalid constraints[{index}]: {error}") from error
        raw_examples = data.get("example_dialogues", [])
        if not isinstance(raw_examples, list):
            raise ValueError("invalid character JSON schema (example_dialogues must be an array)")
        examples: list[ExampleDialogue] = []
        for index, raw_example in enumerate(raw_examples):
            if not isinstance(raw_example, dict):
                raise ValueError(f"example_dialogues[{index}] must be an object")
            _require_fields(raw_example, frozenset({"user", "character"}), f"example_dialogues[{index}]")
            if raw_example.keys() - {"user", "character"}:
                raise ValueError(f"example_dialogues[{index}] contains unexpected fields")
            try:
                examples.append(ExampleDialogue(raw_example["user"], raw_example["character"]))
            except (TypeError, ValueError) as error:
                raise ValueError(f"invalid example_dialogues[{index}]: {error}") from error
        try:
            card = CharacterCard(
                character_id=data["character_id"],
                name=data["name"],
                age=identity.get("age"),
                gender=identity.get("gender", ""),
                occupation=identity.get("occupation", ""),
                portrait=identity.get("portrait"),
                personality=data["personality"],
                background=data["background"],
                goals=data["goals"],
                constraints=tuple(constraints),
                example_dialogues=tuple(examples),
                identity_editable=data.get("identity_editable", True),
            )
        except (TypeError, ValueError) as error:
            raise ValueError(f"invalid character card in {path}: {error}") from error
        result = self._validator.validate(card)
        if not result.valid:
            raise ValueError("character card validation failed: " + "; ".join(result.errors))
        return card
