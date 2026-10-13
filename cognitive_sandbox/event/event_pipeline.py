from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import replace

from cognitive_sandbox.event.event_bus import EventBus
from cognitive_sandbox.domain.world_events import WorldEvent


class KnowledgeEventListener:
    """Record an event as scoped direct knowledge for its acting participant."""

    def __init__(self, store, propagation_engine=None):
        self.store = store
        if propagation_engine is None:
            from cognitive_sandbox.knowledge.propagation.propagation_engine import PropagationEngine
            propagation_engine = PropagationEngine()
        self.propagation_engine = propagation_engine

    def handle_event(self, event, context=None):
        from cognitive_sandbox.knowledge.models.world_fact import WorldFact
        # ObserveHandler already creates de-duplicated OBSERVED records with
        # the correct perception source; do not downgrade them to DIRECT.
        if event.event_type == "observe_action":
            return ()
        participants = tuple(dict.fromkeys(
            value for value in (event.actor_id, event.target_id)
            if value and value.casefold() not in {"system", "director"}
        ))
        if not participants:
            return ()
        fact_id = f"fact_{event.event_id}"
        if self.store.get_fact(fact_id) is not None:
            return ()
        description = event.payload.get("description")
        content = description if isinstance(description, str) and description.strip() else f"事件：{event.event_type}"
        fact = WorldFact(
            fact_id, content, event.event_type, event.timestamp or "world-event",
            tuple(dict.fromkeys((event.actor_id, event.target_id) if event.target_id else (event.actor_id,))),
            max(0.0, min(1.0, float(event.payload.get("importance", 0.5))))
            if isinstance(event.payload.get("importance", 0.5), (int, float))
            and not isinstance(event.payload.get("importance", 0.5), bool) else 0.5,
        )
        self.store.add_fact(fact)
        records = self.propagation_engine.propagate(fact, participants=participants)
        for record in records:
            self.store.add_knowledge(record)
        return records


class EventPipeline:
    """Publish world events once, then fan them out to registered world services."""

    def __init__(self, bus: EventBus | None = None, *, event_timeline=None,
                 knowledge_handler=None, relationship_manager=None,
                 npc_response_service=None, autonomous_scheduler=None, scheduler=None,
                 world_evolution_engine=None, world_memory=None):
        self.bus = bus or EventBus()
        self.world_evolution_engine = world_evolution_engine
        self.event_timeline = event_timeline
        self.relationship_manager = relationship_manager
        self.autonomous_scheduler = autonomous_scheduler
        if knowledge_handler is None:
            # A store is supplied explicitly by the owning runtime; no global
            # world-state access is introduced by the pipeline.
            knowledge_handler = None
        self.knowledge_handler = knowledge_handler
        self.npc_response_service = npc_response_service
        self.scheduler = scheduler
        self.world_memory = None
        if world_evolution_engine is not None:
            self.bus.subscribe(world_evolution_engine, name="world_evolution")
        if event_timeline is not None:
            self.bus.subscribe(lambda event, _context: event_timeline.record_event(event), name="history")
        if world_memory is not None:
            self.set_world_memory(world_memory)
        if knowledge_handler is not None:
            callback = knowledge_handler if callable(knowledge_handler) else getattr(knowledge_handler, "handle_event", None)
            if callable(callback):
                self.bus.subscribe(lambda event, context: _invoke(callback, event, context), name="knowledge")
        if relationship_manager is not None:
            self.bus.subscribe(self._handle_relationship, name="relationship")
        if npc_response_service is not None:
            self.bus.subscribe(self._handle_npc, name="npc_response")
        if autonomous_scheduler is not None:
            self.bus.subscribe(self._handle_autonomous, name="autonomous_npc")
        if scheduler is not None:
            self.bus.subscribe(self._handle_scheduler, name="scheduler")

    def subscribe(self, listener, *, name=None, event_types=()):
        return self.bus.subscribe(listener, name=name, event_types=event_types)

    def set_world_memory(self, world_memory):
        """Attach a passive recorder to already-applied event notifications."""
        if self.world_memory is world_memory:
            return
        self.world_memory = world_memory
        if not any(item.name == "world_memory" for item in self.bus.listeners):
            self.bus.subscribe_before(world_memory, "history", name="world_memory")

    def subscribe_before(self, listener, before, *, name=None, event_types=()):
        return self.bus.subscribe_before(listener, before, name=name, event_types=event_types)

    def publish(self, event: WorldEvent, *, context=None, allow_npc_response=True) -> tuple[WorldEvent, ...]:
        if not isinstance(event, WorldEvent):
            raise TypeError("event must be a WorldEvent.")
        clock = getattr(context, "world_clock", None)
        if event.timestamp is None and clock is not None:
            event = replace(event, timestamp=clock.current_time().isoformat())
        published = []
        pending = deque(((event, allow_npc_response),))
        seen = set()
        # Prevent accidental listener feedback loops while allowing ordinary cascades.
        while pending and len(published) < 256:
            current, allow_npc = pending.popleft()
            if current.event_id in seen:
                continue
            seen.add(current.event_id)
            published.append(current)
            results = self.bus.publish(current, context, exclude=() if allow_npc else ("npc_response",))
            for listener_name, value in results:
                if listener_name == "npc_response" and not allow_npc:
                    continue
                for child in _world_events(value):
                    pending.append((child, False if listener_name in {"scheduler", "autonomous_npc", "npc_response"} else True))
        return tuple(published)

    def _handle_npc(self, event, context):
        if self.npc_response_service is None or context is None:
            return ()
        contextual = getattr(self.npc_response_service, "handle_event_with_context", None)
        if callable(contextual):
            return contextual(event, context)
        return self.npc_response_service.handle_event(event, getattr(context, "agent_contexts", ()))

    def _handle_relationship(self, event, _context):
        manager = self.relationship_manager
        if manager is None:
            return ()
        before = {(item.source_id, item.target_id): item for item in manager.relationships}
        result = manager.apply_event(event)
        if self.world_memory is not None:
            after = {(item.source_id, item.target_id): item for item in manager.relationships}
            for pair in sorted(set(before) | set(after)):
                old, new = before.get(pair), after.get(pair)
                if old != new:
                    self.world_memory.record_relationship(
                        pair[0], pair[1], before=_relationship_summary(old),
                        after=_relationship_summary(new), timestamp=event.timestamp,
                        cause=f"world event:{event.event_type}",
                    )
        return result

    def _handle_scheduler(self, event, context):
        if self.scheduler is None:
            return ()
        callback = getattr(self.scheduler, "handle_event", None)
        if callable(callback):
            return callback(event, context)
        if callable(self.scheduler):
            return self.scheduler(event, context)
        return ()

    def _handle_autonomous(self, event, context):
        if self.autonomous_scheduler is None:
            return ()
        callback = getattr(self.autonomous_scheduler, "handle_event", None)
        if callable(callback):
            return callback(event, context)
        return ()


def _invoke(callback: Callable, event, context):
    try:
        return callback(event, context)
    except TypeError:
        return callback(event)


def _world_events(value):
    if isinstance(value, WorldEvent):
        return (value,)
    if value is None or isinstance(value, (str, bytes, dict)):
        return ()
    try:
        return tuple(item for item in value if isinstance(item, WorldEvent))
    except TypeError:
        return ()


def _relationship_summary(state):
    if state is None:
        return None
    return {name: getattr(state, name) for name in (
        "trust", "respect", "fear", "affinity", "hostility",
    )}
