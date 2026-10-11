from __future__ import annotations

from dataclasses import dataclass

from cognitive_sandbox.domain.scenario_content import ScenarioContent
from cognitive_sandbox.domain.validation_result import ValidationResult


@dataclass(frozen=True)
class WorldGenerationResult:
    """A validated, human-reviewable world draft or an explicit failure."""

    scenario_content: ScenarioContent | None
    validation_result: ValidationResult
    warnings: tuple[str, ...] = ()
    error: str | None = None

    def __post_init__(self) -> None:
        if self.scenario_content is not None and not isinstance(
            self.scenario_content, ScenarioContent
        ):
            raise TypeError("scenario_content must be a ScenarioContent or None.")
        if not isinstance(self.validation_result, ValidationResult):
            raise TypeError("validation_result must be a ValidationResult.")
        warnings = tuple(self.warnings)
        if any(not isinstance(item, str) or not item.strip() for item in warnings):
            raise ValueError("warnings must contain non-empty strings.")
        object.__setattr__(self, "warnings", warnings)
        if self.error is not None and (
            not isinstance(self.error, str) or not self.error.strip()
        ):
            raise ValueError("error must be a non-empty string or None.")
        if self.validation_result.valid:
            if self.scenario_content is None or self.error is not None:
                raise ValueError("a successful result requires content and cannot have an error.")
        elif self.scenario_content is not None or self.error is None:
            raise ValueError("a failed result requires an error and cannot contain draft content.")
