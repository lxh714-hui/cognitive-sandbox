from __future__ import annotations

from dataclasses import dataclass, replace

from cognitive_sandbox.goal.character_goal import CharacterGoal
from .goal_history import GoalHistoryEntry
from .goal_state import GoalLifecycleState, GoalState
from .goal_transition import GoalTransition
from .goal_transition_rule import GoalTransitionRule


@dataclass(frozen=True)
class GoalLifecycleSnapshot:
    states: tuple[GoalState, ...] = ()
    history: tuple[GoalHistoryEntry, ...] = ()
    transitions: tuple[GoalTransition, ...] = ()

    def __post_init__(self):
        for name, model in (("states", GoalState), ("history", GoalHistoryEntry), ("transitions", GoalTransition)):
            values = tuple(getattr(self, name))
            if any(not isinstance(item, model) for item in values):
                raise TypeError(f"{name} must contain {model.__name__} values.")
            object.__setattr__(self, name, values)


class GoalLifecycleManager:
    """Track richer goal lifecycle states while preserving CharacterGoal's legacy status API."""

    def __init__(self, goal_manager, rules=(), snapshot: GoalLifecycleSnapshot | None = None):
        self.goal_manager = goal_manager
        self.rules = tuple(rules)
        if any(not isinstance(item, GoalTransitionRule) for item in self.rules):
            raise TypeError("rules must contain GoalTransitionRule values.")
        snapshot = snapshot or GoalLifecycleSnapshot()
        if not isinstance(snapshot, GoalLifecycleSnapshot):
            raise TypeError("snapshot must be GoalLifecycleSnapshot.")
        self._states = {item.goal_id: item for item in snapshot.states}
        self._history = list(snapshot.history)
        self._transitions = list(snapshot.transitions)
        self._transitioned = {item.source_goal_id for item in snapshot.transitions}
        for goal in getattr(goal_manager, "goals", ()):
            self._states.setdefault(goal.goal_id, GoalState(goal.goal_id, goal.owner_id, _state_for(goal), goal.progress))

    @property
    def states(self):
        return tuple(self._states[key] for key in sorted(self._states))

    @property
    def history(self):
        return tuple(self._history)

    @property
    def transitions(self):
        return tuple(self._transitions)

    def state_for(self, goal_id):
        return self._states.get(goal_id)

    def evaluate(self, *, source_event_id="", timestamp=""):
        """Apply progress thresholds to current goals; returns newly created goals."""
        created = []
        for goal in tuple(getattr(self.goal_manager, "goals", ())):
            state = self._states.get(goal.goal_id, GoalState(goal.goal_id, goal.owner_id, _state_for(goal), goal.progress))
            self._states.setdefault(goal.goal_id, state)
            if goal.status != "active":
                continue
            if goal.progress > state.progress:
                state = self._record_progress(state, goal.progress, timestamp)
                self._states[goal.goal_id] = state
            matching = next((rule for rule in self.rules if rule.source_goal in {goal.goal_type, goal.goal_id}
                             and self._condition_met(rule.condition, goal)), None)
            if matching is not None and goal.goal_id not in self._transitioned:
                previous = state.state
                self.goal_manager.update(goal.owner_id, goal.goal_type, status="completed", progress=1.0)
                self._set_state(goal, GoalLifecycleState.TRANSFORMED, 1.0,
                                f"目标条件满足：{matching.condition}", source_event_id, timestamp)
                next_goal = CharacterGoal(
                    owner_id=goal.owner_id,
                    description=matching.result_description or matching.result.replace("_", " "),
                    goal_type=matching.result,
                    priority=matching.result_priority,
                    conditions=matching.result_conditions,
                    goal_id=f"{goal.owner_id}:{matching.result}",
                    parent_goal_id=goal.goal_id,
                )
                if self.goal_manager.by_id(next_goal.goal_id) is None:
                    self.goal_manager.add(next_goal)
                    created.append(next_goal)
                    self._states[next_goal.goal_id] = GoalState(next_goal.goal_id, next_goal.owner_id, GoalLifecycleState.ACTIVE, 0)
                    self._history.append(GoalHistoryEntry(goal.owner_id, next_goal.goal_id, GoalLifecycleState.PENDING,
                                                          GoalLifecycleState.ACTIVE, "由前置目标转化生成",
                                                          source_event_id, timestamp))
                self._transitions.append(GoalTransition(goal.owner_id, goal.goal_id, next_goal.goal_id,
                                                        source_event_id or f"goal:{goal.goal_id}",
                                                        matching.condition, timestamp))
                self._transitioned.add(goal.goal_id)
                continue
            next_state = _state_for(goal)
            if next_state != state.state or goal.progress != state.progress:
                self._set_state(goal, next_state, goal.progress, "目标进度更新", source_event_id, timestamp)
        return tuple(created)

    def set_status(self, goal_id, state, *, reason, source_event_id="", timestamp=""):
        goal = self.goal_manager.by_id(goal_id)
        if goal is None:
            raise KeyError(goal_id)
        state = state if isinstance(state, GoalLifecycleState) else GoalLifecycleState(state)
        legacy = "completed" if state in {GoalLifecycleState.SATISFIED, GoalLifecycleState.TRANSFORMED} else "paused" if state in {GoalLifecycleState.BLOCKED, GoalLifecycleState.FAILED} else "active"
        self.goal_manager.replace_goal(__import__("dataclasses").replace(goal, status=legacy))
        return self._set_state(goal, state, goal.progress, reason, source_event_id, timestamp)

    def snapshot(self):
        return GoalLifecycleSnapshot(self.states, self.history, self.transitions)

    def record_action_feedback(self, goal_id, *, action_type, timestamp="", result="completed",
                               effectiveness=0.5, progress_delta=0.0, event_id=""):
        """Attach an observed action outcome to a goal without deciding its outcome."""
        goal = self.goal_manager.by_id(goal_id)
        if goal is None:
            raise KeyError(goal_id)
        for name, value in (("action_type", action_type), ("result", result)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if isinstance(effectiveness, bool) or not isinstance(effectiveness, (int, float)) or not 0 <= effectiveness <= 1:
            raise ValueError("effectiveness must be between 0 and 1.")
        if isinstance(progress_delta, bool) or not isinstance(progress_delta, (int, float)):
            raise ValueError("progress_delta must be numeric.")
        state = self._states.get(goal_id, GoalState(goal_id, goal.owner_id, _state_for(goal), goal.progress))
        identifier = event_id or f"feedback:{goal_id}:{len(state.recent_action_feedback)}"
        if any(item[0] == identifier for item in state.recent_action_feedback):
            return state
        feedback = (*state.recent_action_feedback,
                    (identifier, action_type, str(timestamp or ""), result, float(effectiveness), float(progress_delta)))[-20:]
        samples = state.progress_samples
        if timestamp:
            samples = (*samples, (str(timestamp), float(goal.progress)))[-10:]
        successful = float(progress_delta) > 0 or result in {"progress", "effective", "success"}
        if successful:
            stagnation = state.stagnation_level * 0.6
            if stagnation < .001:
                stagnation = 0.0
            frustration = max(0.0, state.frustration_level - 0.2)
        else:
            weak_count = sum(1 for item in feedback[-10:] if item[4] < .35 or item[3] in {
                "no_new_information", "failed", "ineffective",
            })
            stagnation = min(1.0, .7 * weak_count / 10 + .3 * _elapsed_fraction(
                samples[0][0] if samples else "", timestamp, 10,
            ))
            frustration = min(1.0, state.frustration_level * .75 + (1.0 - float(effectiveness)) * .25)
        velocity = state.progress_velocity
        if float(progress_delta) > 0:
            velocity = _velocity(samples, float(progress_delta))
        elif len(samples) >= 2:
            velocity = _velocity(samples, 0.0)
        updated = replace(state, progress=goal.progress, progress_velocity=velocity,
                          stagnation_level=stagnation, frustration_level=frustration,
                          recent_action_feedback=feedback, progress_samples=samples)
        self._states[goal_id] = updated
        return updated

    @property
    def maximum_stagnation(self):
        return max((item.stagnation_level for item in self.states
                    if item.state in {GoalLifecycleState.ACTIVE, GoalLifecycleState.PROGRESSING}), default=0.0)

    @property
    def pressures(self):
        """Current explicit blockers derived from goal progress feedback."""
        from cognitive_sandbox.conflict.conflict_state import GoalPressure
        return tuple(GoalPressure(item.goal_id, "stagnation",
                                  max(item.stagnation_level, item.frustration_level))
                     for item in self.states
                     if item.state in {GoalLifecycleState.ACTIVE, GoalLifecycleState.PROGRESSING}
                     and max(item.stagnation_level, item.frustration_level) >= .3)

    def restore(self, snapshot):
        if not isinstance(snapshot, GoalLifecycleSnapshot):
            raise TypeError("snapshot must be GoalLifecycleSnapshot.")
        self._states = {item.goal_id: item for item in snapshot.states}
        self._history = list(snapshot.history)
        self._transitions = list(snapshot.transitions)
        self._transitioned = {item.source_goal_id for item in snapshot.transitions}

    def _set_state(self, goal, state, progress, reason, event_id, timestamp):
        old = self._states.get(goal.goal_id, GoalState(goal.goal_id, goal.owner_id, GoalLifecycleState.PENDING, 0))
        previous = old.state
        value = replace(old, state=state, progress=progress)
        self._states[goal.goal_id] = value
        if previous != state:
            self._history.append(GoalHistoryEntry(goal.owner_id, goal.goal_id, previous, state, reason, event_id, timestamp))
        return value

    @staticmethod
    def _record_progress(state, progress, timestamp):
        samples = (*state.progress_samples, (str(timestamp or ""), float(progress)))[-10:]
        delta = max(0.0, float(progress) - state.progress)
        return replace(state, progress=float(progress), progress_velocity=_velocity(samples, delta),
                       stagnation_level=state.stagnation_level * .6,
                       frustration_level=max(0.0, state.frustration_level - .2),
                       progress_samples=samples)

    @staticmethod
    def _condition_met(condition, goal):
        text = condition.strip().casefold().replace(" ", "")
        if text.startswith("progress>="):
            try:
                return goal.progress >= float(text.split(">=", 1)[1])
            except ValueError:
                return False
        if text.startswith("progress>"):
            try:
                return goal.progress > float(text.split(">", 1)[1])
            except ValueError:
                return False
        if text == "completed":
            return goal.status == "completed"
        return False


def _state_for(goal):
    if goal.status == "completed":
        return GoalLifecycleState.SATISFIED
    if goal.status == "paused":
        return GoalLifecycleState.BLOCKED
    return GoalLifecycleState.PROGRESSING if goal.progress > 0 else GoalLifecycleState.ACTIVE


def _velocity(samples, fallback_delta):
    valid = [(when, progress) for when, progress in samples if when]
    if len(valid) < 2:
        return min(1.0, max(0.0, fallback_delta))
    try:
        from datetime import datetime
        start = datetime.fromisoformat(valid[0][0].replace("Z", "+00:00"))
        end = datetime.fromisoformat(valid[-1][0].replace("Z", "+00:00"))
        days = max((end - start).total_seconds() / 86400, 1 / 24)
        return min(1.0, max(0.0, (valid[-1][1] - valid[0][1]) / days))
    except (TypeError, ValueError):
        return min(1.0, max(0.0, fallback_delta))


def _elapsed_fraction(start, end, days):
    if not start or not end:
        return 0.0
    try:
        from datetime import datetime
        first = datetime.fromisoformat(start.replace("Z", "+00:00"))
        last = datetime.fromisoformat(end.replace("Z", "+00:00"))
        fraction = min(1.0, max(0.0, (last - first).total_seconds() / 86400 / days))
        return 0.0 if fraction < .001 else fraction
    except (TypeError, ValueError):
        return 0.0
