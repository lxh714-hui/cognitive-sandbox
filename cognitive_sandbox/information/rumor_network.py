from dataclasses import dataclass

from .clue import Clue
from .rumor import Rumor
from .information_path import InformationPath


@dataclass(frozen=True)
class RumorNetworkSnapshot:
    clues: tuple[Clue, ...] = ()
    rumors: tuple[Rumor, ...] = ()
    paths: tuple[InformationPath, ...] = ()
    processed_event_ids: tuple[str, ...] = ()

    def __post_init__(self):
        for field, expected in (("clues", Clue), ("rumors", Rumor), ("paths", InformationPath)):
            values = tuple(getattr(self, field))
            if any(not isinstance(item, expected) for item in values):
                raise TypeError(f"{field} must contain {expected.__name__} values")
            object.__setattr__(self, field, values)
        processed = tuple(self.processed_event_ids)
        if any(not isinstance(item, str) or not item.strip() for item in processed):
            raise ValueError("processed_event_ids must contain non-empty strings")
        object.__setattr__(self, "processed_event_ids", processed)


class RumorNetwork:
    """World-local information graph; character-facing queries remain owner scoped."""
    def __init__(self, snapshot: RumorNetworkSnapshot | None = None):
        snapshot = snapshot or RumorNetworkSnapshot()
        self._clues = {item.clue_id: item for item in snapshot.clues}
        self._rumors = list(snapshot.rumors)
        self._paths = list(snapshot.paths)
        self._processed = set(snapshot.processed_event_ids)

    @property
    def clues(self):
        return tuple(self._clues[key] for key in sorted(self._clues))

    @property
    def rumors(self):
        return tuple(self._rumors)

    @property
    def paths(self):
        return tuple(self._paths)

    def snapshot(self):
        return RumorNetworkSnapshot(self.clues, tuple(self._rumors), tuple(self._paths), tuple(sorted(self._processed)))

    def has_processed(self, event_id):
        return event_id in self._processed

    def mark_processed(self, event_id):
        self._processed.add(event_id)

    def add_clue(self, clue):
        if not isinstance(clue, Clue):
            raise TypeError("clue must be Clue")
        if clue.clue_id not in self._clues:
            self._clues[clue.clue_id] = clue

    def add_rumor(self, rumor):
        if not isinstance(rumor, Rumor):
            raise TypeError("rumor must be Rumor")
        if not any(item.rumor_id == rumor.rumor_id for item in self._rumors):
            self._rumors.append(rumor)

    def add_path(self, path):
        if not isinstance(path, InformationPath):
            raise TypeError("path must be InformationPath")
        self._paths.append(path)

    def for_character(self, character_id):
        """Return only rumors currently held by this character, never graph-wide nodes."""
        return tuple(item for item in self._rumors if item.current_holder == character_id)
