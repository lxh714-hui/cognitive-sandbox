from __future__ import annotations

import re
from collections.abc import Mapping

from cognitive_sandbox.world_evolution.state_change import StateChange


RULE_PRIMITIVES = frozenset({
    "set_state", "modify_value", "modify_relationship", "create_event", "create_opportunity",
})


class ScenarioRuleResolver:
    """Translate declarative scenario rules into generic immutable state deltas.

    A rule has an ``event_type`` trigger, optional generic ``when`` predicates,
    and an ordered ``effects`` list. The resolver contains no scenario-specific
    behavior and never executes code from a package.
    """

    def __init__(self, rules=()):
        if hasattr(rules, "rules") and hasattr(rules, "scenario_id"):
            rules = rules.rules
        self.rules = tuple(_mapping(rule) for rule in rules)

    @classmethod
    def from_runtime(cls, runtime):
        """Create a resolver solely from the validated runtime contract."""
        from cognitive_sandbox.domain.scenario_runtime import ScenarioRuntime

        if not isinstance(runtime, ScenarioRuntime):
            raise TypeError("runtime must be a ScenarioRuntime")
        return cls(runtime.rules)

    def resolve(self, event, *, resource_manager, location_manager, goal_manager, state_values=None,
                relationship_values=None):
        state_values = state_values or {}
        relationship_values = relationship_values or {}
        changes = []
        projected = {}
        for rule in self.rules:
            if rule["event_type"] != event.event_type:
                continue
            if not self._conditions_match(rule.get("when", ()), event, resource_manager,
                                          location_manager, goal_manager, projected, state_values):
                continue
            for effect in rule["effects"]:
                change = self._resolve_effect(effect, event, resource_manager, location_manager,
                                              goal_manager, projected, state_values, relationship_values)
                if change is None or change.old_value == change.new_value:
                    continue
                changes.append(change)
                projected[(change.target_type, change.target_id, change.field)] = change.new_value
        return tuple(changes)

    def _conditions_match(self, conditions, event, resources, locations, goals, projected, state_values):
        for condition in conditions:
            target_type, target_id = self._resolve_target(condition["target"], event, goals)
            if not target_id:
                return False
            # Availability predicates observe the event-entry inventory. An
            # ordered rule may consume the last unit and still apply the other
            # effects that were authorized by that same pre-event condition.
            value = None if target_type == "resource" else projected.get(
                (target_type, target_id, condition["field"])
            )
            if value is None:
                value = _read(target_type, target_id, condition["field"], resources, locations, goals, state_values)
            if not _compare(value, condition["operator"], condition["value"]):
                return False
        return True

    def _resolve_effect(self, effect, event, resources, locations, goals, projected, state_values,
                        relationship_values):
        kind = effect["type"]
        if kind == "modify_relationship":
            source, target = _interpolate(effect["source"], event), _interpolate(effect["target"], event)
            target_id = f"{source}->{target}"
            field = effect.get("field", "trust")
            old = projected.get(("relationship", target_id, field), relationship_values.get((target_id, field), 0))
            return StateChange("relationship", target_id, field, old, old + effect["delta"],
                               effect.get("reason", f"Scenario rule applied for {event.event_type}"),
                               event.event_id, event.timestamp)
        if kind == "create_event":
            value = {"event_type": effect["event_type"], "payload": effect.get("payload", {})}
            return StateChange("event", event.event_id, "pending", None, value,
                               effect.get("reason", f"Scenario rule applied for {event.event_type}"),
                               event.event_id, event.timestamp)
        if kind == "create_opportunity":
            value = effect["template"]
            opportunity_id = str(value.get("opportunity_id", event.event_id))
            return StateChange("opportunity", opportunity_id, "pending", None, value,
                               effect.get("reason", f"Scenario rule applied for {event.event_type}"),
                               event.event_id, event.timestamp)

        target_type, target_id = self._resolve_target(effect["target"], event, goals)
        if not target_id:
            return None
        field = effect["field"]
        key = (target_type, target_id, field)
        old = projected.get(key)
        if old is None:
            old = _read(target_type, target_id, field, resources, locations, goals, state_values)
        if kind == "set_state":
            new = _interpolate(effect["value"], event)
        else:
            old = 0 if old is None else old
            new = old + effect["delta"]
        if isinstance(new, (int, float)) and not isinstance(new, bool):
            if "minimum" in effect:
                new = max(effect["minimum"], new)
            if "maximum" in effect:
                new = min(effect["maximum"], new)
        return StateChange(target_type, target_id, field, old, new,
                           effect.get("reason", f"Scenario rule applied for {event.event_type}"),
                           event.event_id, event.timestamp)

    @staticmethod
    def _resolve_target(target, event, goals):
        kind = target["type"]
        if kind == "goal":
            identity = target.get("id")
            if identity is not None:
                identity = _interpolate(identity, event)
            else:
                selected = goals.get(_interpolate(target["owner_id"], event), target["goal_type"])
                identity = selected.goal_id if selected is not None else None
            return kind, identity
        return kind, _interpolate(target["id"], event)


def validate_rule_collection(rules, known_targets=None):
    """Validate package-authored rules without evaluating or mutating them."""
    errors = []
    if not isinstance(rules, (tuple, list)):
        return ("evolution_rules must be a sequence",)
    known_targets = known_targets or {}
    for index, rule in enumerate(rules):
        prefix = f"evolution_rules[{index}]"
        if not isinstance(rule, Mapping):
            errors.append(f"{prefix} must be an object")
            continue
        if _contains_executable_content(rule):
            errors.append(f"{prefix} contains prohibited executable content")
        event_type = rule.get("event_type")
        if not isinstance(event_type, str) or not event_type.strip():
            errors.append(f"{prefix}.event_type must not be empty")
        effects = rule.get("effects")
        if not isinstance(effects, (tuple, list)) or not effects:
            errors.append(f"{prefix}.effects must be a non-empty sequence")
            continue
        when = rule.get("when", ())
        if not isinstance(when, (tuple, list)):
            errors.append(f"{prefix}.when must be a sequence")
        else:
            for condition_index, condition in enumerate(when):
                errors.extend(_validate_condition(condition, f"{prefix}.when[{condition_index}]", known_targets))
        for effect_index, effect in enumerate(effects):
            errors.extend(_validate_effect(effect, f"{prefix}.effects[{effect_index}]", known_targets))
    return tuple(errors)


def _validate_effect(effect, label, known_targets):
    errors = []
    if not isinstance(effect, Mapping):
        return (f"{label} must be an object",)
    kind = effect.get("type")
    if kind not in RULE_PRIMITIVES:
        return (f"{label}.type is not a registered rule primitive",)
    if kind in {"set_state", "modify_value"}:
        errors.extend(_validate_target(effect.get("target"), f"{label}.target", known_targets))
        if not _nonempty(effect.get("field")):
            errors.append(f"{label}.field must not be empty")
        if kind == "set_state" and "value" not in effect:
            errors.append(f"{label}.value is required")
        if kind == "modify_value" and not _number(effect.get("delta")):
            errors.append(f"{label}.delta must be numeric")
    elif kind == "modify_relationship":
        for key in ("source", "target"):
            if not _nonempty(effect.get(key)):
                errors.append(f"{label}.{key} must not be empty")
            elif key in {"source", "target"} and not _known_entity_reference(effect[key], known_targets):
                errors.append(f"{label}.{key} references an unknown entity")
        if not _number(effect.get("delta")):
            errors.append(f"{label}.delta must be numeric")
    elif kind == "create_event":
        if not _nonempty(effect.get("event_type")):
            errors.append(f"{label}.event_type must not be empty")
        if "payload" in effect and not isinstance(effect["payload"], Mapping):
            errors.append(f"{label}.payload must be an object")
    elif kind == "create_opportunity":
        if not isinstance(effect.get("template"), Mapping):
            errors.append(f"{label}.template must be an object")
    return tuple(errors)


def _validate_condition(condition, label, known_targets):
    if not isinstance(condition, Mapping):
        return (f"{label} must be an object",)
    errors = list(_validate_target(condition.get("target"), f"{label}.target", known_targets))
    if not _nonempty(condition.get("field")):
        errors.append(f"{label}.field must not be empty")
    if condition.get("operator") not in {"eq", "ne", "lt", "lte", "gt", "gte", "contains"}:
        errors.append(f"{label}.operator is not supported")
    if "value" not in condition:
        errors.append(f"{label}.value is required")
    return tuple(errors)


def _validate_target(target, label, known_targets):
    if not isinstance(target, Mapping):
        return (f"{label} must be an object",)
    kind, identity = target.get("type"), target.get("id")
    errors = []
    if kind not in {"entity", "location", "item", "resource", "goal"}:
        errors.append(f"{label}.type is not supported")
    if not _nonempty(identity):
        # Goal selectors may use owner_id and goal_type instead of a generated id.
        if kind != "goal" or not (_nonempty(target.get("owner_id")) and _nonempty(target.get("goal_type"))):
            errors.append(f"{label}.id must not be empty")
        elif "goal" in known_targets and target["goal_type"] not in known_targets["goal"]:
            errors.append(f"{label} references unknown goal: {target['goal_type']}")
        elif ("entity" in known_targets and target["owner_id"] not in known_targets["entity"]
              and not any(token in target["owner_id"] for token in ("$event_actor", "$event_location", "$parameter."))):
            errors.append(f"{label} references unknown goal owner: {target['owner_id']}")
    elif kind in known_targets and identity not in known_targets[kind] and "$event_" not in identity and "$parameter." not in identity:
        base_identity = identity.partition("@")[0] if kind == "resource" else identity
        if base_identity not in known_targets[kind]:
            errors.append(f"{label} references unknown {kind}: {identity}")
    return tuple(errors)


def _read(kind, identity, field, resources, locations, goals, state_values):
    if kind == "location":
        target = locations.get(identity)
        if target is None:
            return None
        if field in getattr(target, "properties", {}):
            return target.properties[field]
        return getattr(target, field, None)
    if kind == "resource":
        resource_type, _, location_id = identity.partition("@")
        if field == "quantity":
            return resources.quantity(resource_type, location_id=location_id or None)
    if kind == "goal":
        target = goals.by_id(identity)
        return getattr(target, field, None) if target is not None else None
    return state_values.get((kind, identity, field))


def _compare(left, operator, right):
    try:
        return {
            "eq": lambda: left == right, "ne": lambda: left != right,
            "lt": lambda: left < right, "lte": lambda: left <= right,
            "gt": lambda: left > right, "gte": lambda: left >= right,
            "contains": lambda: right in left,
        }[operator]()
    except (KeyError, TypeError, ValueError):
        return False


def _interpolate(value, event):
    if value == "$event_location":
        parameters = event.payload.get("parameters", {})
        nested = parameters.get("location") if isinstance(parameters, Mapping) else None
        return event.location or nested or event.payload.get("location")
    if value == "$event_actor":
        return event.actor_id
    if isinstance(value, str) and value.startswith("$parameter."):
        parameters = event.payload.get("parameters", {})
        return parameters.get(value.partition(".")[2]) if isinstance(parameters, Mapping) else None
    if isinstance(value, str):
        parameters = event.payload.get("parameters", {})
        location = event.location or (parameters.get("location") if isinstance(parameters, Mapping) else None)
        location = location or event.payload.get("location")
        replacements = {"$event_actor": event.actor_id, "$event_location": location}
        if isinstance(parameters, Mapping):
            replacements.update({f"$parameter.{key}": item for key, item in parameters.items()})
        for token, replacement in replacements.items():
            if token in value:
                value = value.replace(token, "" if replacement is None else str(replacement))
    return value


def _contains_executable_content(value):
    prohibited = {"python", "eval", "callback", "function", "function_ref", "callable", "script"}
    if isinstance(value, Mapping):
        return any(str(key).casefold() in prohibited or _contains_executable_content(item)
                   for key, item in value.items())
    if isinstance(value, (tuple, list)):
        return any(_contains_executable_content(item) for item in value)
    if callable(value):
        return True
    if isinstance(value, str):
        lowered = value.strip().casefold()
        return any(marker in lowered for marker in ("eval(", "exec(", "lambda ", "python:", "callback:", "function_ref:"))
    return False


def _mapping(rule):
    if not isinstance(rule, Mapping):
        raise TypeError("scenario rules must be mappings")
    errors = validate_rule_collection((rule,))
    if errors:
        raise ValueError("invalid scenario rule: " + "; ".join(errors))
    return rule


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _known_entity_reference(value, known_targets):
    if not isinstance(value, str):
        return False
    if "$event_actor" in value or "$event_location" in value or "$parameter." in value:
        return True
    return "entity" not in known_targets or value in known_targets["entity"]
