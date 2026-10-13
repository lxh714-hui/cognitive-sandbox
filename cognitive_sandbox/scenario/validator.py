from __future__ import annotations

from cognitive_sandbox.domain.scenario_runtime import ScenarioRuntime
from cognitive_sandbox.domain.validation_result import ValidationResult
from cognitive_sandbox.application.scenario_rule_resolver import validate_rule_collection


class ScenarioRuntimeValidator:
    """Validate the generic runtime envelope without interpreting its data."""

    def validate(self, runtime: ScenarioRuntime) -> ValidationResult:
        errors = []
        if not isinstance(runtime, ScenarioRuntime):
            return ValidationResult(False, ("runtime must be a ScenarioRuntime",), ())
        if not runtime.scenario_id.strip():
            errors.append("scenario_id must not be empty")
        target_sets = {"entity": set(), "location": set(), "item": set(), "resource": set(), "goal": set()}
        for entity in runtime.entities:
            kind = entity.get("kind")
            identity = entity.get("id")
            if kind == "character":
                kind = "entity"
            if kind in target_sets and isinstance(identity, str):
                target_sets[kind].add(identity)
        errors.extend(validate_rule_collection(runtime.rules, target_sets))
        return ValidationResult(not errors, tuple(errors), ())
