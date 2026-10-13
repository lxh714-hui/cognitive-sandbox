from __future__ import annotations

from collections.abc import Iterable


class ActionHandlerRegistry:
    """Map open-vocabulary intent labels to application handlers."""

    def __init__(self, handlers: Iterable[tuple[str, object]] = ()) -> None:
        self._handlers: dict[str, object] = {}
        for intent, handler in handlers:
            self.register(intent, handler)

    def register(self, intent: str, handler: object) -> None:
        if not isinstance(intent, str) or not intent.strip():
            raise ValueError("intent must not be empty")
        if not callable(getattr(handler, "handle", None)):
            raise TypeError("handler must provide handle()")
        self._handlers[intent.strip().casefold()] = handler

    def get(self, intent: str):
        if not isinstance(intent, str):
            return None
        return self._handlers.get(intent.strip().casefold())

    def supports(self, intent: str) -> bool:
        return self.get(intent) is not None

    @property
    def intents(self) -> tuple[str, ...]:
        return tuple(self._handlers)
