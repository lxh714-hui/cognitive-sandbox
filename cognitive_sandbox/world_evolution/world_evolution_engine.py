from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.goal.goal_manager import GoalManager
from cognitive_sandbox.world_evolution.evolution_rule import EvolutionRule
from cognitive_sandbox.world_evolution.location_state import LocationManager, LocationState
from cognitive_sandbox.world_evolution.resource_manager import ResourceManager
from cognitive_sandbox.world_evolution.state_change import StateChange


class WorldEvolutionEngine:
    """Apply deterministic event rules to independent resource, location and goal services."""

    DEFAULT_RULES = (
        EvolutionRule("npc_materials_collected", "resource", "quantity", "increment", 1, "NPC 收集到修复材料"),
        EvolutionRule("npc_patrolled", "location", "safety", "increment", 5, "巡逻提升了区域安全度"),
    )

    def __init__(self, *, resource_manager=None, location_manager=None, goal_manager=None, rules=None,
                 state_changes=(), processed_event_ids=()):
        self.resource_manager = resource_manager or ResourceManager()
        self.location_manager = location_manager or LocationManager()
        self.goal_manager = goal_manager or GoalManager()
        self.rules = tuple(self.DEFAULT_RULES if rules is None else rules)
        if any(not isinstance(rule, EvolutionRule) for rule in self.rules):
            raise TypeError("rules must contain EvolutionRule values.")
        self._state_changes = list(state_changes)
        if any(not isinstance(item, StateChange) for item in self._state_changes):
            raise TypeError("state_changes must contain StateChange values.")
        self._processed_event_ids = set(processed_event_ids)

    @property
    def state_changes(self) -> tuple[StateChange, ...]:
        return tuple(self._state_changes)

    @property
    def processed_event_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._processed_event_ids))

    def handle_event(self, event: WorldEvent, context=None) -> tuple[StateChange, ...]:
        if not isinstance(event, WorldEvent):
            raise TypeError("event must be WorldEvent.")
        if event.event_id in self._processed_event_ids:
            return ()
        self._processed_event_ids.add(event.event_id)
        before = len(self._state_changes)
        if event.event_type == "npc_materials_collected":
            self._collect_materials(event)
        elif event.event_type in {"doctor_repaired_clinic", "npc_clinic_repaired", "clinic_repaired"}:
            self._repair_clinic(event)
        elif event.event_type == "npc_patrolled":
            self._patrol(event)
        elif event.event_type in {"npc_investigated", "npc_observed", "npc_organized", "npc_socialized",
                                  "npc_worked", "npc_rested", "npc_traveled"}:
            self._advance_goal_from_agency(event)
        else:
            self._apply_configured_rules(event)
        return tuple(self._state_changes[before:])

    def _advance_goal_from_agency(self, event):
        """Record small, event-backed goal progress for a completed NPC activity."""
        parameters = event.payload.get("parameters", {})
        effect = parameters.get("goal_effect", {}) if isinstance(parameters, Mapping) else {}
        if isinstance(effect, Mapping) and effect.get("result") in {"no_new_information", "failed", "ineffective"}:
            return
        goal_id = parameters.get("goal_id") if isinstance(parameters, Mapping) else None
        goal = self.goal_manager.by_id(goal_id) if isinstance(goal_id, str) and goal_id else None
        if goal is None:
            goal_type = parameters.get("goal_type") if isinstance(parameters, Mapping) else None
            goal = next((item for item in self.goal_manager.for_character(event.actor_id)
                         if item.goal_type == goal_type), None)
        if goal is None or goal.status != "active":
            return
        amount = effect.get("progress_delta", .03) if isinstance(effect, Mapping) else .03
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount <= 0:
            return
        updated = self.goal_manager.update(
            goal.owner_id, goal.goal_type, progress=min(.99, goal.progress + float(amount)),
        )
        self._record(event, "goal", updated.goal_id, "progress", goal.progress,
                     updated.progress, "角色完成了一项与目标相关的主动行动")

    def _collect_materials(self, event):
        location_id = _action_location(event) or "clinic"
        old_quantity = self.resource_manager.quantity("medical_supplies", location_id=location_id)
        resource = self.resource_manager.add("medical_supplies", 1, location_id=location_id)
        self._record(event, "resource", f"medical_supplies@{location_id}", "quantity", old_quantity, old_quantity + 1, "NPC 收集到修复材料")
        goal = self.goal_manager.get(event.actor_id, "collect_materials")
        if goal is not None:
            progress = min(1.0, goal.progress + 0.2)
            status = "completed" if progress >= 1 else "active"
            self._update_goal(event, goal, progress, status, "完成一批医疗物资收集")
        self._activate_goal(event.actor_id, "restore_power")

    def _repair_clinic(self, event):
        location_id = _action_location(event) or "clinic"
        location = self._ensure_location(location_id, "医疗站" if location_id == "clinic" else location_id)
        if self.resource_manager.quantity("medical_supplies", location_id=location_id) < 1:
            return
        before_quantity = self.resource_manager.quantity("medical_supplies", location_id=location_id)
        self.resource_manager.consume("medical_supplies", 1, location_id=location_id)
        after_quantity = self.resource_manager.quantity("medical_supplies", location_id=location_id)
        self._record(event, "resource", f"medical_supplies@{location_id}", "quantity", before_quantity, after_quantity, "修复医疗站消耗了医疗材料")
        new_progress = min(100.0, location.repair_progress + 20.0)
        new_power = new_progress >= 100.0
        new_status = "operational" if new_power else "under_repair"
        updated = self.location_manager.update(location_id, repair_progress=new_progress, power=new_power, status=new_status)
        self._record(event, "location", location_id, "repair_progress", location.repair_progress, updated.repair_progress, "医疗站修复进度增加")
        self._record(event, "location", location_id, "power", location.power, updated.power, "医疗站供电状态随修复进度更新")
        self._record(event, "location", location_id, "status", location.status, updated.status, "医疗站状态随修复进度更新")
        goal = self.goal_manager.get(event.actor_id, "restore_power")
        if goal is not None:
            progress = new_progress / 100.0
            status = "completed" if new_power else "active"
            self._update_goal(event, goal, progress, status, "医疗站修复进度更新")
        if not new_power:
            self._activate_goal(event.actor_id, "collect_materials")

    def _patrol(self, event):
        location_id = _action_location(event) or self.location_manager.current_location_id or "current"
        location = self._ensure_location(location_id, location_id)
        updated = self.location_manager.adjust_safety(location_id, 5)
        self._record(event, "location", location_id, "safety", location.safety, updated.safety, "巡逻提升了区域安全度")

    def _activate_goal(self, owner_id, goal_type):
        goal = self.goal_manager.get(owner_id, goal_type)
        if goal is not None and goal.status == "paused":
            self.goal_manager.update(owner_id, goal_type, status="active")

    def _update_goal(self, event, goal, progress, status, reason):
        updated = self.goal_manager.update(goal.owner_id, goal.goal_type, progress=progress, status=status)
        self._record(event, "goal", updated.goal_id, "progress", goal.progress, updated.progress, reason)
        if status != goal.status:
            self._record(event, "goal", updated.goal_id, "status", goal.status, status, reason)
        parent = self.goal_manager.by_id(updated.parent_goal_id) if updated.parent_goal_id else None
        if parent is not None:
            self._record(event, "goal", parent.goal_id, "progress", None, parent.progress, "子目标进度汇总到主目标")

    def _apply_configured_rules(self, event):
        for rule in self.rules:
            if rule.event_type != event.event_type:
                continue
            if rule.target_type == "location":
                location_id = rule.target_id or _action_location(event) or self.location_manager.current_location_id or "current"
                location = self._ensure_location(location_id, location_id)
                old = getattr(location, rule.field)
                new = old + rule.value if rule.operation == "increment" else rule.value
                if rule.field == "safety":
                    new = max(0.0, min(100.0, new))
                self.location_manager.update(location_id, **{rule.field: new})
                self._record(event, rule.target_type, location_id, rule.field, old, new, rule.reason)
            elif rule.target_type == "resource" and rule.field == "quantity":
                location_id = rule.target_id or _action_location(event)
                resource_type = str(event.payload.get("resource_type", "medical_supplies"))
                old = self.resource_manager.quantity(resource_type, location_id=location_id)
                amount = rule.value
                if rule.operation == "increment":
                    self.resource_manager.add(resource_type, amount, location_id=location_id)
                    new = old + amount
                    self._record(event, "resource", f"{resource_type}@{location_id or ''}", "quantity", old, new, rule.reason)

    def _ensure_location(self, location_id, name):
        location = self.location_manager.get(location_id)
        if location is None:
            location = self.location_manager.add(LocationState(location_id, name))
        return location

    def _record(self, event, target_type, target_id, field, old, new, reason):
        if old == new:
            return
        self._state_changes.append(StateChange(target_type, target_id, field, old, new, reason, event.event_id, event.timestamp))

    def restore(self, *, state_changes=(), processed_event_ids=()):
        values = tuple(state_changes)
        if any(not isinstance(item, StateChange) for item in values):
            raise TypeError("state_changes must contain StateChange values.")
        self._state_changes = list(values)
        self._processed_event_ids = set(processed_event_ids)


def _action_location(event):
    parameters = event.payload.get("parameters", {})
    if isinstance(parameters, Mapping):
        value = parameters.get("location")
        if isinstance(value, str) and value.strip():
            return value
    for key in ("location_id", "location"):
        value = event.payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None
