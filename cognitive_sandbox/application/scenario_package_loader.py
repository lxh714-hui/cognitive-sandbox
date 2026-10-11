from __future__ import annotations

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
        {"scenario_id", "name", "description", "initial_world_state", "character_templates"}
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
            _require_fields(scenario_data, self.SCENARIO_FIELDS, "scenario")
            scenario = Scenario(
                scenario_id=scenario_data["scenario_id"],
                name=scenario_data["name"],
                description=scenario_data["description"],
                initial_world_state=scenario_data["initial_world_state"],
                character_templates=scenario_data["character_templates"],
            )
        except (TypeError, ValueError) as error:
            raise ValueError(f"invalid scenario package metadata in {root}: {error}") from error
        scenario_result = self._scenario_validator.validate(scenario)
        if not scenario_result.valid:
            raise ValueError("scenario validation failed: " + "; ".join(scenario_result.errors))

        world_document = self._world_loader.load(root / "world.json")
        characters = tuple(
            self._character_loader.load(path)
            for path in self._card_paths(root, "characters", "character.json", "character_")
        )
        events = tuple(
            self._event_loader.load(path)
            for path in self._card_paths(root, "events", "event.json", "event_")
        )
        return ScenarioContent(scenario, world_document, characters, events)

    @staticmethod
    def _card_paths(root: Path, directory_name: str, single_name: str, prefix: str) -> tuple[Path, ...]:
        directory = root / directory_name
        if directory.is_dir():
            files = tuple(sorted(path for path in directory.glob("*.json") if path.is_file()))
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
