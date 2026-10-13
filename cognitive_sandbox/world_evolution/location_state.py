from __future__ import annotations

from dataclasses import dataclass, replace
from collections.abc import Mapping


def _freeze_property(value):
    if isinstance(value, Mapping):
        return tuple(sorted((str(key), _freeze_property(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_property(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_property(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError("location properties must contain immutable JSON-compatible values.")


@dataclass(frozen=True)
class LocationState:
    location_id: str
    name: str
    status: str = "active"
    safety: float = 0.0
    power: bool | None = None
    tags: tuple[str, ...] = ()
    properties: tuple[tuple[str, object], ...] = ()

    def __getattr__(self, name):
        # Scenario-defined state fields remain data, not engine model fields.
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return dict(object.__getattribute__(self, "properties"))[name]
        except KeyError as error:
            raise AttributeError(name) from error

    def __post_init__(self):
        for name in ("location_id", "name", "status"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if isinstance(self.safety, bool) or not isinstance(self.safety, (int, float)) or not 0 <= self.safety <= 100:
            raise ValueError("safety must be between 0 and 100.")
        object.__setattr__(self, "safety", float(self.safety))
        if self.power is not None and not isinstance(self.power, bool):
            raise TypeError("power must be bool or None.")
        tags = tuple(self.tags)
        if any(not isinstance(item, str) or not item.strip() for item in tags):
            raise ValueError("tags must contain non-empty strings.")
        object.__setattr__(self, "tags", tags)
        properties = self.properties
        if isinstance(properties, Mapping):
            properties = tuple(sorted(properties.items()))
        else:
            properties = tuple(properties)
        if any(not isinstance(key, str) or not key.strip() for key, _ in properties):
            raise ValueError("properties must have non-empty string keys.")
        object.__setattr__(self, "properties", tuple((key, _freeze_property(value)) for key, value in properties))


class LocationManager:
    def __init__(self, locations=(), *, current_location_id: str | None = None):
        self._locations = {}
        self.current_location_id = current_location_id
        for location in locations:
            self.add(location)

    @property
    def locations(self):
        return tuple(self._locations[key] for key in sorted(self._locations))

    def add(self, location: LocationState):
        if not isinstance(location, LocationState):
            raise TypeError("location must be LocationState.")
        if location.location_id in self._locations:
            raise ValueError(f"location already exists: {location.location_id}")
        self._locations[location.location_id] = location
        if self.current_location_id is None:
            self.current_location_id = location.location_id
        return location

    def get(self, location_id: str) -> LocationState | None:
        return self._locations.get(location_id)

    def update(self, location_id: str, **changes) -> LocationState:
        current = self._locations.get(location_id)
        if current is None:
            raise KeyError(location_id)
        known_fields = {"location_id", "name", "status", "safety", "power", "tags", "properties"}
        dynamic = {key: value for key, value in changes.items() if key not in known_fields}
        if dynamic:
            properties = dict(current.properties)
            properties.update(dynamic)
            changes = {**{key: value for key, value in changes.items() if key in known_fields},
                       "properties": tuple(sorted(properties.items()))}
        updated = replace(current, **changes)
        self._locations[location_id] = updated
        return updated

    def value(self, location_id: str, field: str):
        location = self.get(location_id)
        if location is None:
            return None
        return dict(location.properties).get(field, getattr(location, field, None))

    def adjust_safety(self, location_id: str, delta: float) -> LocationState:
        current = self._locations[location_id]
        return self.update(location_id, safety=max(0.0, min(100.0, current.safety + delta)))

    def restore(self, locations, *, current_location_id=None):
        values = tuple(locations)
        if any(not isinstance(item, LocationState) for item in values):
            raise TypeError("locations must contain LocationState values.")
        if len({item.location_id for item in values}) != len(values):
            raise ValueError("location IDs must be unique.")
        self._locations = {item.location_id: item for item in values}
        self.current_location_id = current_location_id if current_location_id in self._locations else next(iter(self._locations), None)
