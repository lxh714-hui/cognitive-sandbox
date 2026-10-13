from __future__ import annotations

from .opportunity_manager import OpportunityManager


class NarrativeOpportunityService:
    """Build player/NPC-scoped opportunity views from current runtime services."""

    def __init__(self, *, world_clock, goal_manager=None, goal_lifecycle_manager=None,
                 conflict_manager=None, location_manager=None, information_manager=None,
                 relationship_lifecycle_manager=None, world_state_provider=None,
                 manager=None):
        self.world_clock = world_clock
        self.goal_manager = goal_manager
        self.goal_lifecycle_manager = goal_lifecycle_manager
        self.conflict_manager = conflict_manager
        self.location_manager = location_manager
        self.information_manager = information_manager
        self.relationship_lifecycle_manager = relationship_lifecycle_manager
        self.world_state_provider = world_state_provider or (lambda: {})
        self.manager = manager or OpportunityManager()

    def for_character(self, character_id, *, limit=None):
        now = self.world_clock.current_time()
        goals = tuple(goal for goal in getattr(self.goal_manager, "goals", ())
                      if goal.owner_id == character_id and goal.status == "active")
        states = tuple(self.goal_lifecycle_manager.state_for(goal.goal_id)
                       for goal in goals) if self.goal_lifecycle_manager is not None else ()
        states = tuple(item for item in states if item is not None)
        information = {}
        if self.information_manager is not None:
            information[character_id] = self.information_manager.received_for(character_id, limit=100)
        current_location = getattr(self.location_manager, "current_location_id", None)
        if current_location is None and self.location_manager is not None:
            current_location = getattr(self.location_manager, "current_location", None)
        self.manager.refresh(
            world_time=now,
            active_goals=goals,
            goal_states=states,
            active_conflicts=tuple(conflict for conflict in getattr(self.conflict_manager, "active_conflicts", ())
                                   if character_id in conflict.participants),
            location_states=tuple(getattr(self.location_manager, "locations", ())),
            information_by_character=information,
            relationship_events=tuple(getattr(self.relationship_lifecycle_manager, "events", ())),
            current_location=current_location,
            visible_character_ids=(character_id,),
            world_state=self.world_state_provider(),
        )
        return self.manager.visible_to(character_id, current_time=now, limit=limit)

    def register(self, opportunity):
        return self.manager.register(opportunity)

    def resolve(self, opportunity_id, *, timestamp=None, cause="opportunity resolved"):
        return self.manager.resolve(opportunity_id, timestamp=timestamp, cause=cause)

    def snapshot(self):
        self.manager.refresh(world_time=self.world_clock.current_time())
        return self.manager.snapshot()

    def restore(self, opportunities):
        self.manager.restore(opportunities)
