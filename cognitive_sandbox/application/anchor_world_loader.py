from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from cognitive_sandbox.cognition import AttentionProfile, CognitiveStyle, ReasoningProfile
from cognitive_sandbox.domain.character_card import CharacterCard
from cognitive_sandbox.domain.constraint import Constraint
from cognitive_sandbox.domain.event_card import EventCard
from cognitive_sandbox.domain.scenario import Scenario
from cognitive_sandbox.domain.scenario_content import ScenarioContent
from cognitive_sandbox.domain.world_document import WorldDocument
from cognitive_sandbox.emotion.emotional_state import EmotionalState
from cognitive_sandbox.narrative.narrative_state import NarrativeState
from cognitive_sandbox.narrative.narrative_thread import NarrativeThread, NarrativeThreadStatus


@dataclass(frozen=True)
class AnchorWorldCard:
    world_id: str
    name: str
    genre: str
    tone: str
    description: str
    rules: tuple[str, ...]
    content_version: str = "0.1"

    def __post_init__(self):
        for field in ("world_id", "name", "genre", "tone", "description", "content_version"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must not be empty.")
        rules = tuple(self.rules)
        if not rules or any(not isinstance(item, str) or not item.strip() for item in rules):
            raise ValueError("rules must contain non-empty strings.")
        object.__setattr__(self, "rules", rules)


@dataclass(frozen=True)
class AnchorWorldPackage:
    world_card: AnchorWorldCard
    scenario_content: ScenarioContent
    locations: tuple[Mapping, ...]
    initial_knowledge: Mapping
    cognitive_styles: Mapping
    reasoning_profiles: Mapping
    attention_profiles: Mapping
    emotion_states: Mapping
    authorities: Mapping
    motivations: tuple
    narrative_state: NarrativeState
    location_relations: tuple[Mapping, ...] = ()
    routines: Mapping = None


class AnchorWorldLoader:
    """Load the versioned Anchor world package as configuration, without starting play."""

    PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "worlds" / "anchor"

    def __init__(self, package_path: str | Path | None = None):
        self.package_path = Path(package_path) if package_path is not None else self.PACKAGE_ROOT

    def load(self) -> AnchorWorldPackage:
        root = self.package_path
        world_data = _read_json(root / "world_card.json")
        required = ("world_id", "name", "genre", "tone", "description", "rules", "initial_state")
        if any(not isinstance(world_data.get(key), str if key in {"world_id", "name", "genre", "tone", "description"} else (list if key == "rules" else dict))
               for key in required):
            raise ValueError("Anchor world_card.json has missing or invalid required fields.")
        if not world_data["rules"] or not world_data["initial_state"]:
            raise ValueError("Anchor world card requires rules and initial state.")

        cards = tuple(self._character(path) for path in sorted((root / "characters").glob("*.json")))
        if not cards:
            raise ValueError("Anchor package contains no character cards.")
        character_ids = {card.character_id for card in cards}
        if len(character_ids) != len(cards):
            raise ValueError("Anchor package contains duplicate character IDs.")
        configs = {item["character_id"]: item for item in (
            _read_json(path) for path in sorted((root / "characters").glob("*.json"))
        )}
        if set(configs) != character_ids:
            raise ValueError("Anchor character configuration IDs do not match character cards.")

        locations = tuple(_freeze(_read_json(path)) for path in sorted((root / "locations").glob("*.json"))
                          if path.name != "location_relations.json")
        if not locations or any(not item.get("location_id") or not item.get("name") for item in locations):
            raise ValueError("Anchor package contains invalid location data.")
        relation_path = root / "locations" / "location_relations.json"
        location_relations = tuple(_freeze(item) for item in _read_json(relation_path)) if relation_path.exists() else ()
        location_ids = {item["location_id"] for item in locations}
        for relation in location_relations:
            if relation.get("from") not in location_ids or relation.get("to") not in location_ids:
                raise ValueError("Anchor location relation references an unknown location.")
            for field in ("distance", "traffic", "social_density", "information_flow", "anomaly_relevance"):
                if field not in relation:
                    raise ValueError(f"Anchor location relation is missing {field}.")
                if isinstance(relation[field], bool) or not isinstance(relation[field], (int, float)) or not 0 <= relation[field] <= 1:
                    raise ValueError(f"Anchor location relation {field} must be between 0 and 1.")
        routines = {}
        routines_dir = root / "characters" / "routines"
        for path in sorted(routines_dir.glob("*.json")) if routines_dir.exists() else ():
            routine = _read_json(path)
            character_id = routine.get("character_id")
            if character_id not in character_ids or character_id in routines:
                raise ValueError("Anchor routine references an unknown or duplicate character.")
            if not isinstance(routine.get("activities", ()), list) or not isinstance(routine.get("locations", {}), dict):
                raise ValueError("Anchor routine activities and locations have invalid formats.")
            routines[character_id] = _freeze(routine)
        knowledge = _read_json(root / "knowledge" / "initial_knowledge.json")
        if not isinstance(knowledge, dict) or set(knowledge) != character_ids:
            raise ValueError("Anchor initial knowledge must provide entries for every package character only.")
        if any(not isinstance(records, list) or any(
            not isinstance(record, dict) or not all(isinstance(record.get(field), str) and record[field].strip()
                                                    for field in ("id", "content", "type"))
            for record in records
        ) for records in knowledge.values()):
            raise ValueError("Anchor initial knowledge records are malformed.")

        threads_data = _read_json(root / "narratives" / "initial_threads.json")
        threads = []
        for item in threads_data:
            if not isinstance(item, dict) or set(item.get("participants", ())) - character_ids:
                raise ValueError("Anchor narrative thread references unknown characters.")
            threads.append(NarrativeThread(
                item["id"], item["title"], tuple(item["participants"]), item["conflict"],
                item.get("pressure", 0), item.get("progress", 0), item.get("status", "DORMANT"),
            ))
        events_data = _read_json(root / "events" / "initial_events.json")
        events = tuple(EventCard(**item) for item in events_data)
        if any(set(event.participants) - character_ids for event in events):
            raise ValueError("Anchor initial event references unknown characters.")

        world = WorldDocument(world_data["world_id"], world_data["name"], world_data["description"],
                              tuple(world_data.get("history", ())), tuple(world_data["rules"]))
        world_card = AnchorWorldCard(
            world_data["world_id"], world_data["name"], world_data["genre"], world_data["tone"],
            world_data["description"], tuple(world_data["rules"]), world_data.get("content_version", "0.1"),
        )
        state = dict(world_data["initial_state"])
        state.setdefault("location", world_data.get("initial_location", ""))
        state["locations"] = tuple(dict(item) for item in locations)
        scenario = Scenario(
            "anchor_world", world.name, world.description, state,
            tuple({"id": card.character_id, "name": card.name, "role": card.occupation or "character",
                   "traits": card.personality, "goals": card.goals}
                  for card in cards),
        )
        content = ScenarioContent(scenario, world, cards, events)

        from cognitive_sandbox.authority.authority_level import AuthorityLevel
        from cognitive_sandbox.authority.character_authority import CharacterAuthority
        from cognitive_sandbox.motivation.character_motivation import CharacterMotivation
        authorities = {}
        styles, reasoning, attention, emotions, motivations = {}, {}, {}, {}, []
        for character_id, item in configs.items():
            level = AuthorityLevel[item.get("authority", "IMPORTANT_CHARACTER")]
            authorities[character_id] = (CharacterAuthority.player(character_id) if level is AuthorityLevel.PLAYER
                                         else CharacterAuthority.important_character(character_id))
            cog = item.get("cognition", {})
            styles[character_id] = CognitiveStyle(**{key: cog[key] for key in (
                "analytical", "intuitive", "creative", "suspicious", "pragmatic", "emotional", "strategic"
            ) if key in cog})
            reasoning[character_id] = ReasoningProfile(**{key: cog[key] for key in (
                "reasoning_depth", "reflection_tendency", "causal_search", "future_prediction"
            ) if key in cog})
            attention_values = dict(cog.get("attention", {}))
            pattern_recognition = cog.get("pattern_recognition")
            if isinstance(pattern_recognition, (int, float)) and not isinstance(pattern_recognition, bool):
                attention_values["temporal_pattern"] = max(
                    float(attention_values.get("temporal_pattern", .5)), float(pattern_recognition)
                )
            attention[character_id] = AttentionProfile(**attention_values)
            emotions[character_id] = EmotionalState(**item.get("emotion", {}))
            if item.get("motivation"):
                motivations.append(CharacterMotivation(character_id, **item["motivation"]))

        return AnchorWorldPackage(
            world_card, content, locations, _freeze(knowledge), MappingProxyType(styles),
            MappingProxyType(reasoning), MappingProxyType(attention), MappingProxyType(emotions),
            MappingProxyType(authorities), tuple(motivations), NarrativeState(tuple(threads)),
            location_relations, MappingProxyType(routines),
        )

    @staticmethod
    def _character(path: Path) -> CharacterCard:
        data = _read_json(path)
        constraints = tuple(Constraint(item["type"], item["content"])
                            for item in data.get("constraints", ()))
        return CharacterCard(
            character_id=data["character_id"], name=data["name"], age=data.get("age"),
            gender=data.get("gender", ""), occupation=data.get("occupation", ""),
            personality=tuple(data.get("personality", ())), background=data.get("background", ""),
            goals=tuple(data.get("goals", ())), constraints=constraints,
            identity_editable=data.get("identity_editable", False),
        )


def _read_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"unable to load Anchor package file {path.name}: {error}") from error


def _freeze(value):
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value
