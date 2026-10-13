from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import uuid4


@dataclass(frozen=True)
class WorldResource:
    resource_id: str
    resource_type: str
    quantity: float
    location_id: str | None = None

    def __post_init__(self):
        for name in ("resource_id", "resource_type"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if isinstance(self.quantity, bool) or not isinstance(self.quantity, (int, float)) or self.quantity < 0:
            raise ValueError("quantity must be non-negative.")
        object.__setattr__(self, "quantity", float(self.quantity))
        if self.location_id is not None and (not isinstance(self.location_id, str) or not self.location_id.strip()):
            raise ValueError("location_id must be None or a non-empty string.")


class ResourceManager:
    def __init__(self, resources=()):
        values = tuple(resources)
        if any(not isinstance(item, WorldResource) for item in values):
            raise TypeError("resources must contain WorldResource values.")
        if len({item.resource_id for item in values}) != len(values):
            raise ValueError("resource IDs must be unique.")
        self._resources = {item.resource_id: item for item in values}

    @property
    def resources(self):
        return tuple(self._resources[key] for key in sorted(self._resources))

    def query(self, resource_type: str | None = None, *, location_id: str | None = None) -> tuple[WorldResource, ...]:
        return tuple(item for item in self.resources if (resource_type is None or item.resource_type == resource_type)
                     and (location_id is None or item.location_id == location_id))

    def quantity(self, resource_type: str, *, location_id: str | None = None) -> float:
        return sum(item.quantity for item in self.query(resource_type, location_id=location_id))

    def add(self, resource_type: str, quantity: float, *, location_id: str | None = None, resource_id: str | None = None):
        if isinstance(quantity, bool) or not isinstance(quantity, (int, float)) or quantity <= 0:
            raise ValueError("added quantity must be positive.")
        existing = next((item for item in self.resources if item.resource_type == resource_type and item.location_id == location_id), None)
        if existing is not None:
            updated = replace(existing, quantity=existing.quantity + quantity)
            self._resources[existing.resource_id] = updated
            return updated
        item = WorldResource(resource_id or uuid4().hex, resource_type, quantity, location_id)
        if item.resource_id in self._resources:
            raise ValueError(f"resource already exists: {item.resource_id}")
        self._resources[item.resource_id] = item
        return item

    def consume(self, resource_type: str, quantity: float, *, location_id: str | None = None) -> tuple[WorldResource, ...]:
        if isinstance(quantity, bool) or not isinstance(quantity, (int, float)) or quantity <= 0:
            raise ValueError("consumed quantity must be positive.")
        candidates = list(self.query(resource_type, location_id=location_id))
        available = sum(item.quantity for item in candidates)
        if available < quantity:
            raise ValueError(f"insufficient {resource_type}: requested {quantity}, available {available}.")
        remaining = float(quantity)
        changed = []
        for item in candidates:
            amount = min(item.quantity, remaining)
            remaining -= amount
            updated = replace(item, quantity=item.quantity - amount)
            if updated.quantity == 0:
                del self._resources[item.resource_id]
            else:
                self._resources[item.resource_id] = updated
            changed.append(updated)
            if remaining <= 0:
                break
        return tuple(changed)

    def transfer(self, resource_type: str, quantity: float, *, from_location_id: str | None, to_location_id: str | None):
        self.consume(resource_type, quantity, location_id=from_location_id)
        return self.add(resource_type, quantity, location_id=to_location_id)

    def restore(self, resources):
        values = tuple(resources)
        if any(not isinstance(item, WorldResource) for item in values):
            raise TypeError("resources must contain WorldResource values.")
        if len({item.resource_id for item in values}) != len(values):
            raise ValueError("resource IDs must be unique.")
        self._resources = {item.resource_id: item for item in values}
