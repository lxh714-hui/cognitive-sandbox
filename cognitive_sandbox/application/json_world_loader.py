from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from cognitive_sandbox.application.world_validator import WorldValidator
from cognitive_sandbox.domain.world_document import WorldDocument


class JsonWorldLoader:
    REQUIRED_FIELDS = frozenset({"world_id", "name", "description", "history", "rules"})

    def __init__(self, validator: WorldValidator | None = None) -> None:
        self._validator = validator or WorldValidator()

    def load(self, path: str | Path) -> WorldDocument:
        data = _read_json_object(path, "world")
        _require_fields(data, self.REQUIRED_FIELDS, "world")
        try:
            document = WorldDocument(
                world_id=data["world_id"],
                name=data["name"],
                description=data["description"],
                history=data["history"],
                rules=data["rules"],
            )
        except (TypeError, ValueError) as error:
            raise ValueError(f"invalid world document in {path}: {error}") from error
        result = self._validator.validate(document)
        if not result.valid:
            raise ValueError("world document validation failed: " + "; ".join(result.errors))
        return document


def _read_json_object(path: str | Path, label: str) -> dict[str, Any]:
    source = Path(path)
    try:
        with source.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
    except FileNotFoundError as error:
        raise ValueError(f"{label} JSON file not found: {source}") from error
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"could not read {label} JSON at {source}: {error}") from error
    if not isinstance(data, dict):
        raise ValueError(f"{label} JSON root must be an object: {source}")
    return data


def _require_fields(data: Mapping[str, Any], required: frozenset[str], label: str) -> None:
    missing = sorted(required - data.keys())
    unexpected = sorted(data.keys() - required)
    if missing or unexpected:
        details = []
        if missing:
            details.append("missing fields: " + ", ".join(missing))
        if unexpected:
            details.append("unexpected fields: " + ", ".join(unexpected))
        raise ValueError(f"invalid {label} JSON schema (" + "; ".join(details) + ")")
