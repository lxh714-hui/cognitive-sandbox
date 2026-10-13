from __future__ import annotations

from dataclasses import replace

from cognitive_sandbox.goal.character_goal import CharacterGoal


class GoalManager:
    """Own system-created goal trees and expose immutable snapshots."""

    def __init__(self, goals=(), *, last_evaluated_tick: str | None = None):
        self._goals: dict[str, CharacterGoal] = {}
        self.last_evaluated_tick = last_evaluated_tick
        for goal in goals:
            self.add(goal)

    @property
    def goals(self):
        return tuple(self._goals[key] for key in sorted(self._goals))

    def add(self, goal: CharacterGoal):
        if not isinstance(goal, CharacterGoal):
            raise TypeError("goal must be CharacterGoal.")
        if goal.goal_id in self._goals:
            raise ValueError("goal_id must be unique.")
        parent = self._goals.get(goal.parent_goal_id) if goal.parent_goal_id else None
        if parent is not None and parent.owner_id != goal.owner_id:
            raise ValueError("parent and child goals must have the same owner.")
        self._goals[goal.goal_id] = goal
        return goal

    def for_character(self, owner_id: str):
        return tuple(goal for goal in self.goals if goal.owner_id == owner_id)

    def get(self, owner_id: str, goal_type: str) -> CharacterGoal | None:
        return next((goal for goal in self._goals.values() if goal.owner_id == owner_id and goal.goal_type == goal_type), None)

    def by_id(self, goal_id: str) -> CharacterGoal | None:
        return self._goals.get(goal_id)

    def replace_goal(self, goal: CharacterGoal):
        if not isinstance(goal, CharacterGoal) or goal.goal_id not in self._goals:
            raise KeyError(getattr(goal, "goal_id", None))
        self._goals[goal.goal_id] = goal
        return goal

    def children(self, goal_id: str):
        return tuple(goal for goal in self.goals if goal.parent_goal_id == goal_id)

    def update(self, owner_id: str, goal_type: str, *, progress=None, status=None):
        goal = self.get(owner_id, goal_type)
        if goal is None:
            raise KeyError((owner_id, goal_type))
        changes = {}
        if progress is not None:
            changes["progress"] = progress
        if status is not None:
            changes["status"] = status
        updated = replace(goal, **changes)
        self._goals[goal.goal_id] = updated
        if updated.parent_goal_id:
            self._refresh_parent(updated.parent_goal_id)
        return self._goals[goal.goal_id]

    def _refresh_parent(self, parent_id: str):
        parent = self._goals.get(parent_id)
        if parent is None or not parent.subgoals:
            return
        children = tuple(self._goals[item] for item in parent.subgoals if item in self._goals)
        if not children:
            return
        progress = sum(item.progress for item in children) / len(children)
        complete = len(children) == len(parent.subgoals) and all(item.status == "completed" for item in children)
        self._goals[parent_id] = replace(parent, progress=progress, status="completed" if complete else parent.status)

    def restore(self, goals, *, last_evaluated_tick=None):
        values = tuple(goals)
        if any(not isinstance(goal, CharacterGoal) for goal in values):
            raise TypeError("goals must contain CharacterGoal values.")
        keys = [goal.goal_id for goal in values]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate goal IDs.")
        self._goals = dict(zip(keys, values))
        for goal in values:
            if goal.parent_goal_id and goal.parent_goal_id not in self._goals:
                raise ValueError("goal tree contains an unknown parent.")
            if any(child not in self._goals for child in goal.subgoals):
                raise ValueError("goal tree contains an unknown subgoal.")
        self.last_evaluated_tick = last_evaluated_tick
