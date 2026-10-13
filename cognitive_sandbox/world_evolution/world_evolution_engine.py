from __future__ import annotations

from collections.abc import Mapping

from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.goal.goal_manager import GoalManager
from cognitive_sandbox.world_evolution.location_state import LocationManager
from cognitive_sandbox.world_evolution.resource_manager import ResourceManager
from cognitive_sandbox.world_evolution.state_change import StateChange


class WorldEvolutionEngine:
    """Apply resolved state deltas without embedding scenario rules."""

    def __init__(self, *, resource_manager=None, location_manager=None, goal_manager=None,
                 rule_resolver=None, state_changes=(), processed_event_ids=(),
                 state_values=None, relationship_values=None, pending_events=(), pending_opportunities=(),
                 scenario_runtime=None):
        self.resource_manager = resource_manager or ResourceManager()
        self.location_manager = location_manager or LocationManager()
        self.goal_manager = goal_manager or GoalManager()
        self.rule_resolver = rule_resolver
        if scenario_runtime is not None:
            from cognitive_sandbox.domain.scenario_runtime import ScenarioRuntime
            if not isinstance(scenario_runtime, ScenarioRuntime):
                raise TypeError("scenario_runtime must be a ScenarioRuntime")
        self.scenario_runtime = scenario_runtime
        self._state_changes = list(state_changes)
        if any(not isinstance(item, StateChange) for item in self._state_changes):
            raise TypeError("state_changes must contain StateChange values.")
        self._processed_event_ids = set(processed_event_ids)
        self.state_values = dict(state_values or {})
        self.relationship_values = dict(relationship_values or {})
        self.pending_events = list(pending_events)
        self.pending_opportunities = list(pending_opportunities)

    @property
    def state_changes(self):
        return tuple(self._state_changes)

    @property
    def processed_event_ids(self):
        return tuple(sorted(self._processed_event_ids))

    def handle_event(self, event: WorldEvent, context=None):
        if not isinstance(event, WorldEvent):
            raise TypeError("event must be WorldEvent.")
        if event.event_id in self._processed_event_ids:
            return ()
        self._processed_event_ids.add(event.event_id)
        resolver = self.rule_resolver
        if resolver is None:
            return ()
        deltas = resolver.resolve(
            event,
            resource_manager=self.resource_manager,
            location_manager=self.location_manager,
            goal_manager=self.goal_manager,
            state_values=self.state_values,
            relationship_values=self.relationship_values,
        )
        applied = []
        for delta in deltas:
            if not isinstance(delta, StateChange):
                raise TypeError("rule resolver must return StateChange values.")
            if self._apply_delta(delta):
                self._state_changes.append(delta)
                applied.append(delta)
        return tuple(applied)

    def _apply_delta(self, delta):
        if delta.target_type == "location":
            if self.location_manager.get(delta.target_id) is None:
                return False
            self.location_manager.update(delta.target_id, **{delta.field: delta.new_value})
            return True
        if delta.target_type == "resource" and delta.field == "quantity":
            resource_type, separator, location_id = delta.target_id.partition("@")
            self.resource_manager.set_quantity(
                resource_type, float(delta.new_value),
                location_id=(location_id or None) if separator else None,
            )
            return True
        if delta.target_type == "goal":
            goal = self.goal_manager.by_id(delta.target_id)
            if goal is None or delta.field not in {"progress", "status"}:
                return False
            self.goal_manager.update(
                goal.owner_id, goal.goal_type,
                **{delta.field: delta.new_value},
            )
            return True
        if delta.target_type == "relationship":
            self.relationship_values[(delta.target_id, delta.field)] = delta.new_value
            return True
        if delta.target_type in {"entity", "item", "world"}:
            self.state_values[(delta.target_type, delta.target_id, delta.field)] = delta.new_value
            return True
        if delta.target_type == "event" and delta.field == "pending":
            self.pending_events.append(delta.new_value)
            return True
        if delta.target_type == "opportunity" and delta.field == "pending":
            self.pending_opportunities.append(delta.new_value)
            return True
        return False

    def restore(self, *, state_changes=(), processed_event_ids=(), state_values=None,
                relationship_values=None, pending_events=(), pending_opportunities=()):
        values = tuple(state_changes)
        if any(not isinstance(item, StateChange) for item in values):
            raise TypeError("state_changes must contain StateChange values.")
        self._state_changes = list(values)
        self._processed_event_ids = set(processed_event_ids)
        self.state_values = dict(state_values or {})
        self.relationship_values = dict(relationship_values or {})
        self.pending_events = list(pending_events)
        self.pending_opportunities = list(pending_opportunities)
