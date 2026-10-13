from __future__ import annotations

from cognitive_sandbox.domain.character_card import CharacterCard, ExampleDialogue
from cognitive_sandbox.domain.constraint import Constraint
from cognitive_sandbox.domain.validation_result import ValidationResult


class CharacterCardValidator:
    """Validate character-card fields without changing the card."""

    def validate(self, card: CharacterCard) -> ValidationResult:
        if not isinstance(card, CharacterCard):
            raise TypeError("card must be a CharacterCard.")
        errors: list[str] = []
        for field_name in ("character_id", "name"):
            value = getattr(card, field_name, None)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{field_name} must not be empty.")
        for field_name in ("personality", "goals"):
            values = getattr(card, field_name, None)
            if not isinstance(values, tuple):
                errors.append(f"{field_name} must be a tuple of non-empty strings.")
            elif any(not isinstance(item, str) or not item.strip() for item in values):
                errors.append(f"{field_name} must contain only non-empty strings.")
        if not isinstance(getattr(card, "identity_editable", None), bool):
            errors.append("identity_editable must be a boolean.")
        constraints = getattr(card, "constraints", None)
        if not isinstance(constraints, tuple):
            errors.append("constraints must be a tuple of valid Constraint values.")
        else:
            for index, constraint in enumerate(constraints):
                if not isinstance(constraint, Constraint):
                    errors.append(f"constraints[{index}] must be a Constraint.")
                elif (
                    not isinstance(constraint.type, str)
                    or constraint.type not in Constraint.ALLOWED_TYPES
                ):
                    errors.append(f"constraints[{index}].type is invalid.")
                elif not isinstance(constraint.content, str) or not constraint.content.strip():
                    errors.append(f"constraints[{index}].content must not be empty.")
        examples = getattr(card, "example_dialogues", None)
        if not isinstance(examples, tuple):
            errors.append("example_dialogues must be a tuple of valid ExampleDialogue values.")
        else:
            for index, example in enumerate(examples):
                if not isinstance(example, ExampleDialogue):
                    errors.append(f"example_dialogues[{index}] must be an ExampleDialogue.")
                elif any(
                    not isinstance(value, str) or not value.strip()
                    for value in (example.user, example.character)
                ):
                    errors.append(f"example_dialogues[{index}] fields must not be empty.")
        return ValidationResult(not errors, tuple(errors), ())
