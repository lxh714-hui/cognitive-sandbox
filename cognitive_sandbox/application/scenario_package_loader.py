from __future__ import annotations

import json
from pathlib import Path

from cognitive_sandbox.application.character_card_validator import CharacterCardValidator
from cognitive_sandbox.application.event_card_validator import EventCardValidator
from cognitive_sandbox.application.json_character_loader import JsonCharacterLoader
from cognitive_sandbox.application.json_event_loader import JsonEventLoader
from cognitive_sandbox.application.json_world_loader import JsonWorldLoader, _read_json_object, _require_fields
from cognitive_sandbox.application.scenario_validator import ScenarioValidator
from cognitive_sandbox.application.world_validator import WorldValidator
from cognitive_sandbox.domain.scenario import Scenario
from cognitive_sandbox.domain.scenario_content import ScenarioContent


class ScenarioPackageLoader:
    """Load a directory package containing scenario, world, character and event JSON."""

    SCENARIO_FIELDS = frozenset(
        {"scenario_id", "name", "description", "initial_world_state", "character_templates", "runtime_config"}
    )

    def __init__(
        self,
        *,
        world_loader: JsonWorldLoader | None = None,
        character_loader: JsonCharacterLoader | None = None,
        event_loader: JsonEventLoader | None = None,
        scenario_validator: ScenarioValidator | None = None,
    ) -> None:
        self._world_loader = world_loader or JsonWorldLoader(WorldValidator())
        self._character_loader = character_loader or JsonCharacterLoader(CharacterCardValidator())
        self._event_loader = event_loader or JsonEventLoader(EventCardValidator())
        self._scenario_validator = scenario_validator or ScenarioValidator()

    def load(self, directory: str | Path) -> ScenarioContent:
        root = Path(directory)
        if not root.exists() or not root.is_dir():
            raise ValueError(f"scenario package directory does not exist: {root}")
        try:
            scenario_data = _read_json_object(root / "scenario.json", "scenario")
            # Runtime configuration was added after the original package schema;
            # older world packages remain loadable with the compatibility defaults.
            scenario_data.setdefault("runtime_config", {})
            _require_fields(scenario_data, self.SCENARIO_FIELDS, "scenario")
            runtime_config = dict(scenario_data.get("runtime_config", {}))
            character_paths = self._card_paths(root, "characters", "character.json", "character_")
            character_profiles = {}
            for path in character_paths:
                character_data = _read_json_object(path, "character")
                profile = character_data.get("runtime_profile")
                if profile is not None:
                    character_profiles[character_data["character_id"]] = profile
            if character_profiles:
                runtime_config.setdefault("character_profiles", character_profiles)
            package_data = self._package_runtime_data(root, character_paths)
            for key, value in package_data.items():
                runtime_config.setdefault(key, value)
            scenario = Scenario(
                scenario_id=scenario_data["scenario_id"],
                name=scenario_data["name"],
                description=scenario_data["description"],
                initial_world_state=scenario_data["initial_world_state"],
                character_templates=scenario_data["character_templates"],
                runtime_config=runtime_config,
            )
        except (TypeError, ValueError) as error:
            raise ValueError(f"invalid scenario package metadata in {root}: {error}") from error
        scenario_result = self._scenario_validator.validate(scenario)
        if not scenario_result.valid:
            raise ValueError("scenario validation failed: " + "; ".join(scenario_result.errors))

        world_document = self._world_loader.load(root / "world.json")
        characters = tuple(self._character_loader.load(path) for path in character_paths)
        event_paths = self._card_paths(root, "events", "event.json", "event_")
        events = [self._event_loader.load(path) for path in event_paths]
        for data in self._read_json_array(root / "events" / "initial_events.json"):
            events.append(self._event_loader.from_mapping(data))
        return ScenarioContent(scenario, world_document, characters, tuple(events))

    @staticmethod
    def _read_json_array(path: Path) -> tuple[dict, ...]:
        if not path.is_file():
            return ()
        try:
            with path.open("r", encoding="utf-8") as stream:
                value = json.load(stream)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ValueError(f"could not read package data at {path}: {error}") from error
        if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
            raise ValueError(f"package data must be an array of objects: {path}")
        return tuple(value)

    @classmethod
    def _package_runtime_data(cls, root: Path, character_paths: tuple[Path, ...]) -> dict:
        """Read optional, world-authored runtime data using package conventions."""
        data = {}
        locations_dir = root / "locations"
        if locations_dir.is_dir():
            locations = []
            for path in sorted(locations_dir.glob("*.json")):
                if path.name == "location_relations.json":
                    continue
                locations.append(_read_json_object(path, "location"))
            if locations:
                data["locations"] = tuple(locations)
            relation_path = locations_dir / "location_relations.json"
            if relation_path.is_file():
                data["location_relations"] = cls._read_json_array(relation_path)

        for directory, filename, key, expected in (
            ("knowledge", "initial_knowledge.json", "initial_knowledge", dict),
        ):
            path = root / directory / filename
            if path.is_file():
                value = _read_json_object(path, key)
                if not isinstance(value, expected):
                    raise ValueError(f"{key} package data must be an object.")
                data[key] = value

        threads_path = root / "narratives" / "initial_threads.json"
        if threads_path.is_file():
            data["narrative_threads"] = cls._read_json_array(threads_path)
        events_path = root / "events" / "initial_events.json"
        if events_path.is_file():
            data["initial_events"] = cls._read_json_array(events_path)

        routines_dir = root / "characters" / "routines"
        if routines_dir.is_dir():
            routines = {}
            for path in sorted(routines_dir.glob("*.json")):
                item = _read_json_object(path, "routine")
                character_id = item.get("character_id")
                if not isinstance(character_id, str) or not character_id.strip():
                    raise ValueError(f"routine data must identify its owner: {path}")
                if character_id in routines:
                    raise ValueError(f"duplicate routine data for character: {character_id}")
                routines[character_id] = item
            if routines:
                data["routines"] = routines
        return data

    @staticmethod
    def _card_paths(root: Path, directory_name: str, single_name: str, prefix: str) -> tuple[Path, ...]:
        directory = root / directory_name
        if directory.is_dir():
            files = tuple(sorted(
                path for path in directory.glob("*.json")
                if path.is_file() and path.name != "initial_events.json"
            ))
            if files:
                if directory_name == "characters":
                    files = tuple(
                        sorted(files, key=lambda path: (path.name != "player.json", path.name))
                    )
                return files
        single_file = root / single_name
        if single_file.is_file():
            return (single_file,)
        # Also accept a flat package with multiple explicitly prefixed cards.
        return tuple(sorted(path for path in root.glob(f"{prefix}*.json") if path.is_file()))
