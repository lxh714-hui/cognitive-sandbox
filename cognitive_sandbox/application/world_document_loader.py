from __future__ import annotations

from collections.abc import Iterable

from cognitive_sandbox.domain.world_document import WorldDocument


class WorldDocumentLoader:
    """Load immutable world documents from an in-memory catalog.

    The identifier-based lookup keeps callers independent of the eventual
    backing source, so a JSON catalog can replace the in-memory catalog later.
    """

    def __init__(self, documents: Iterable[WorldDocument] = ()) -> None:
        self._documents: dict[str, WorldDocument] = {}
        for document in documents:
            self.register(document)

    def register(self, document: WorldDocument) -> None:
        if not isinstance(document, WorldDocument):
            raise TypeError("document must be a WorldDocument.")
        self._documents[document.world_id] = document

    def load(self, world_id: str) -> WorldDocument | None:
        if not isinstance(world_id, str):
            raise TypeError("world_id must be a string.")
        return self._documents.get(world_id)
