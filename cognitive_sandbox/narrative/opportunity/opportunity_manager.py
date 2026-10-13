from __future__ import annotations

from dataclasses import replace

from .event_emergence_evaluator import EventEmergenceEvaluator
from .narrative_opportunity import NarrativeOpportunity, OpportunityStatus


class OpportunityManager:
    """Small read-only facade for generating and filtering opportunity snapshots."""

    def __init__(self, evaluator=None, *, world_memory=None):
        self.evaluator = evaluator or EventEmergenceEvaluator()
        self.world_memory = world_memory
        self._latest = ()
        self._persistent = {}

    @property
    def opportunities(self):
        combined = {item.opportunity_id: item for item in self._latest}
        combined.update(self._persistent)
        return tuple(combined.values())

    def refresh(self, **snapshot):
        previous = {item.opportunity_id: item for item in self.opportunities}
        evaluated = self.evaluator.evaluate(**snapshot)
        current_time = snapshot.get("world_time")
        self._latest = tuple(
            replace(item, status=OpportunityStatus.EXPIRED)
            if item.status is OpportunityStatus.ACTIVE and item.is_expired(current_time)
            else item
            for item in evaluated
        )
        for key, item in tuple(self._persistent.items()):
            if item.status is OpportunityStatus.ACTIVE and item.is_expired(current_time):
                self._persistent[key] = replace(item, status=OpportunityStatus.EXPIRED)
        self._record_transitions(previous, current_time)
        return self.opportunities

    def visible_to(self, character_id, *, current_time=None, limit=None):
        values = tuple(item for item in self.opportunities
                       if item.status is OpportunityStatus.ACTIVE
                       and item.is_visible_to(character_id) and not item.is_expired(current_time))
        return values[:max(0, int(limit))] if limit is not None else values

    def for_character(self, character_id, *, current_time=None, **snapshot):
        self.refresh(**snapshot)
        return self.visible_to(character_id, current_time=current_time)

    def register(self, opportunity: NarrativeOpportunity) -> NarrativeOpportunity:
        if not isinstance(opportunity, NarrativeOpportunity):
            raise TypeError("opportunity must be a NarrativeOpportunity.")
        previous = self._persistent.get(opportunity.opportunity_id)
        self._persistent[opportunity.opportunity_id] = opportunity
        if self.world_memory is not None and previous is None:
            self.world_memory.record_opportunity(
                opportunity.opportunity_id, "created", timestamp=opportunity.created_time,
                cause=opportunity.description or "opportunity created",
                metadata={"source_type": getattr(opportunity.source_type, "value", opportunity.source_type),
                          "importance": opportunity.importance},
            )
        return opportunity

    def resolve(self, opportunity_id: str, *, timestamp=None, cause="opportunity resolved") -> NarrativeOpportunity | None:
        item = self._persistent.get(opportunity_id) or next(
            (candidate for candidate in self._latest if candidate.opportunity_id == opportunity_id), None
        )
        if item is None or item.status is not OpportunityStatus.ACTIVE:
            return item
        updated = replace(item, status=OpportunityStatus.RESOLVED)
        self._persistent[opportunity_id] = updated
        if self.world_memory is not None:
            self.world_memory.record_opportunity(
                opportunity_id, "resolved", timestamp=timestamp,
                cause=cause, metadata={"status": updated.status.value},
            )
        return updated

    def snapshot(self) -> tuple[NarrativeOpportunity, ...]:
        combined = {item.opportunity_id: item for item in self._latest}
        combined.update(self._persistent)
        return tuple(combined.values())

    def restore(self, opportunities) -> None:
        values = tuple(opportunities)
        if any(not isinstance(item, NarrativeOpportunity) for item in values):
            raise TypeError("opportunities must contain NarrativeOpportunity values.")
        self._persistent = {item.opportunity_id: item for item in values}

    def _record_transitions(self, previous, timestamp):
        if self.world_memory is None:
            return
        current = {item.opportunity_id: item for item in self.opportunities}
        for key, item in current.items():
            old = previous.get(key)
            if old is None:
                self.world_memory.record_opportunity(
                    key, "created", timestamp=item.created_time or timestamp,
                    cause=item.description or "opportunity created",
                    metadata={"source_type": getattr(item.source_type, "value", item.source_type),
                              "importance": item.importance},
                )
            elif old.status is not item.status:
                action = "expired" if item.status is OpportunityStatus.EXPIRED else item.status.value
                self.world_memory.record_opportunity(
                    key, action, timestamp=timestamp, cause=item.description or action,
                    metadata={"previous_status": old.status.value, "status": item.status.value},
                )
