from dataclasses import dataclass

from cognitive_sandbox.domain.world_instance import WorldInstance
from cognitive_sandbox.simulation_test.simulation_runner import SimulationRunner


@dataclass(frozen=True)
class LongSimulationResult:
    checkpoints: tuple[int, ...]
    reports: tuple[object, ...]
    world_instance_id: str
    checkpoint_results: tuple["LongSimulationCheckpoint", ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "checkpoints", tuple(self.checkpoints))
        object.__setattr__(self, "reports", tuple(self.reports))
        object.__setattr__(self, "checkpoint_results", tuple(self.checkpoint_results))
        if len(self.checkpoints) != len(self.reports):
            raise ValueError("checkpoints and reports must have matching lengths")
        if self.checkpoint_results and len(self.checkpoints) != len(self.checkpoint_results):
            raise ValueError("checkpoint_results must match checkpoints")


@dataclass(frozen=True)
class LongSimulationCheckpoint:
    day: int
    report: object
    cumulative_event_count: int
    npc_action_counts: tuple[tuple[str, int], ...]
    clue_count: int
    rumor_count: int
    information_path_count: int
    relationship_transition_count: int
    goal_transition_count: int
    relationship_stages: tuple[object, ...]
    thread_states: tuple[object, ...]
    emergence_report: object

    def __post_init__(self):
        if isinstance(self.day, bool) or not isinstance(self.day, int) or self.day < 1:
            raise ValueError("day must be a positive integer")
        for name in ("cumulative_event_count", "clue_count", "rumor_count", "information_path_count",
                     "relationship_transition_count", "goal_transition_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        object.__setattr__(self, "npc_action_counts", tuple(tuple(item) for item in self.npc_action_counts))
        object.__setattr__(self, "relationship_stages", tuple(self.relationship_stages))
        object.__setattr__(self, "thread_states", tuple(self.thread_states))


class LongSimulationRunner:
    """Run one persistent runtime cumulatively to long day checkpoints, without probe stimuli."""
    DEFAULT_CHECKPOINTS = (30, 100, 365)

    def __init__(self, launcher=None, runner=None):
        if launcher is None:
            from cognitive_sandbox.application.game_launcher import GameLauncher
            launcher = GameLauncher()
        self.launcher = launcher
        self.runner = runner or SimulationRunner()

    def run_anchor(self, *, checkpoints=None, random_seed=0, enable_player_idle=True, session=None):
        checkpoints = tuple(checkpoints or self.DEFAULT_CHECKPOINTS)
        if any(isinstance(day, bool) or not isinstance(day, int) or day < 1 for day in checkpoints):
            raise ValueError("checkpoints must be positive integer day counts")
        if tuple(sorted(set(checkpoints))) != checkpoints:
            raise ValueError("checkpoints must be strictly increasing")
        session = session or self.launcher.start_anchor_world()
        self._prepare_routine_presence(session)
        clock = session.executor.world_clock
        instance = WorldInstance(
            session.world_instance_id, "anchor_world", session.world_instance_id, "锚点",
            "自然自主模拟检查点。", "active", "running", clock.current_time().isoformat(), session.player_id,
        )
        reports, checkpoint_results, previous = [], [], 0
        background_published = False
        for index, day in enumerate(checkpoints):
            on_start = None
            if not background_published:
                on_start = self._publish_packaged_background
                background_published = True
            report = self.runner.run(
                instance, session=session, tick_count=day - previous,
                random_seed=random_seed + index, enable_player_idle=enable_player_idle,
                on_start=on_start,
            )
            reports.append(report)
            timeline = tuple(session.executor.event_timeline.events)
            action_counts = {}
            for event in timeline:
                if event.event_type.startswith("npc_"):
                    for actor_id in event.actor_ids:
                        action_counts[actor_id] = action_counts.get(actor_id, 0) + 1
            from dataclasses import replace
            from cognitive_sandbox.simulation_test.story_emergence_report import StoryEmergenceAnalyzer
            emergence = StoryEmergenceAnalyzer().analyze(replace(report, events=timeline), session)
            checkpoint_results.append(LongSimulationCheckpoint(
                day, report, len(timeline), tuple(sorted(action_counts.items())),
                len(session.information_manager.clues), len(session.information_manager.rumors),
                len(session.information_manager.paths),
                len(session.relationship_lifecycle_manager.transitions),
                len(session.goal_lifecycle_manager.transitions),
                tuple(session.relationship_lifecycle_manager.stages),
                tuple(report.thread_states), emergence,
            ))
            previous = day
        return LongSimulationResult(checkpoints, tuple(reports), session.world_instance_id,
                                    tuple(checkpoint_results))

    @staticmethod
    def _prepare_routine_presence(session):
        """Let routine-bearing NPCs enter at their configured daily starting locations.

        This is only used by autonomous observation runs. A regular roleplay
        session keeps the package's introduction constraints untouched.
        """
        from cognitive_sandbox.character_presence.entry_rule import EntryRule
        from cognitive_sandbox.character_presence.character_presence import PresenceState

        presence = session.presence_manager
        now = session.executor.world_clock.current_time()
        routines = getattr(session, "anchor_routines", {}) or {}
        for character_id, routine in routines.items():
            if character_id == session.player_id:
                continue
            current = presence.get(character_id)
            if current is None or current.availability not in {PresenceState.UNKNOWN, PresenceState.LEFT}:
                continue
            locations = routine.get("locations", {})
            location = next(iter(locations.values()), None)
            if not location:
                continue
            presence.add_rule(EntryRule(
                character_id, trigger_event_types=("routine_due",), allowed_locations=(location,),
            ))
            available = presence.evaluate_entry(
                character_id, event_type="routine_due", current_location=location,
                current_time=now.isoformat(),
            )
            if available.availability is PresenceState.AVAILABLE:
                presence.introduce(character_id, current_location=location)

    @staticmethod
    def _publish_packaged_background(session, context):
        """Publish configured day-one background information through the normal event path."""
        package = getattr(session, "scenario_content", None)
        card = next((item for item in getattr(package, "event_cards", ())
                     if item.event_type == "neighborhood_rumor"), None)
        if card is None:
            return
        from cognitive_sandbox.domain.world_events import WorldEvent
        event_id = f"{card.event_id}:{session.world_instance_id}"
        if any(item.event_id == event_id for item in session.executor.event_timeline.events):
            return
        event = WorldEvent(
            event_id, "main", session.executor.world_id, card.event_type, "system",
            {"description": card.description, "public_description": card.description,
             "importance": .35, "visibility": "public"},
            0, target_id="pei", location="neighborhood",
            timestamp=session.executor.world_clock.current_time().isoformat(),
        )
        session.executor.event_pipeline.publish(event, context=context)
