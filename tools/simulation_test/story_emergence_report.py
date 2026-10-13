from dataclasses import dataclass


@dataclass(frozen=True)
class EmergenceChain:
    clue_id: str
    source_event_id: str
    information_path: tuple[str, ...]
    decision_event_ids: tuple[str, ...]
    relationship_changes: tuple[str, ...]
    goal_changes: tuple[str, ...]

    def __post_init__(self):
        for field in ("information_path", "decision_event_ids", "relationship_changes", "goal_changes"):
            object.__setattr__(self, field, tuple(getattr(self, field)))


@dataclass(frozen=True)
class StoryEmergenceReport:
    world_instance_id: str
    event_count: int
    chains: tuple[EmergenceChain, ...]
    character_activity: tuple[tuple[str, int], ...]
    relationship_growth: int
    information_flow: int
    narrative_development: int
    emergence_score: float

    def __post_init__(self):
        object.__setattr__(self, "chains", tuple(self.chains))
        object.__setattr__(self, "character_activity", tuple(tuple(item) for item in self.character_activity))
        if not 0 <= self.emergence_score <= 1:
            raise ValueError("emergence_score must be between 0 and 1")


class StoryEmergenceAnalyzer:
    """Organize recorded world changes into evidence-backed event chains."""
    def analyze(self, report, session):
        events = tuple(report.events)
        info = getattr(session, "information_manager", None)
        paths = tuple(info.paths) if info else ()
        event_by_id = {item.event_id: item for item in events}
        chains = []
        activity = {}
        for event in events:
            for actor in event.actor_ids:
                if event.event_type.startswith("npc_"):
                    activity[actor] = activity.get(actor, 0) + 1
        relationships = tuple(getattr(getattr(session, "relationship_lifecycle_manager", None), "transitions", ()))
        goals = tuple(getattr(getattr(session, "goal_lifecycle_manager", None), "transitions", ()))
        for clue in getattr(info, "clues", ()) if info else ():
            clue_paths = tuple(path for path in paths if path.clue_id == clue.clue_id)
            if clue.source_event not in event_by_id and not clue_paths:
                continue
            holders = max((path.holders for path in clue_paths), key=len, default=())
            source_event = event_by_id.get(clue.source_event)
            source_time = getattr(source_event, "timestamp", "") if source_event else clue.created_time
            subsequent = tuple(item.event_id for item in events
                               if item.event_type.startswith("npc_") and set(item.actor_ids) & set(holders)
                               and item.timestamp >= source_time)
            subsequent_set = set(subsequent)
            relation_notes = tuple(
                f"{item.character_a}↔{item.character_b}:{item.previous_stage.value}→{item.new_stage.value}"
                for item in relationships if item.source_event_id in subsequent_set
                and set(holders) & {item.character_a, item.character_b}
            )
            goal_notes = tuple(
                f"{item.owner_id}:{item.source_goal_id}→{item.target_goal_id}"
                for item in goals if item.source_event_id in subsequent_set and item.owner_id in holders
            )
            chains.append(EmergenceChain(clue.clue_id, clue.source_event, holders, subsequent,
                                         relation_notes, goal_notes))
        information_flow = sum(len(path.holders) > 1 for path in paths)
        relationship_growth = len(relationships)
        narrative_development = len(getattr(report, "thread_changes", ()))
        # Score only evidence-backed links; unrelated NPC actions or later
        # relationship changes cannot be attributed to an earlier clue.
        completeness = []
        for chain in chains:
            if not chain.information_path:
                continue
            completeness.append(.4 + (.3 if chain.decision_event_ids else 0.0)
                                + (.2 if chain.relationship_changes else 0.0)
                                + (.1 if chain.goal_changes else 0.0))
        score = sum(completeness) / max(1, len(completeness))
        return StoryEmergenceReport(
            report.world_instance_id, len(events), tuple(chains), tuple(sorted(activity.items())),
            relationship_growth, information_flow, narrative_development, score,
        )
