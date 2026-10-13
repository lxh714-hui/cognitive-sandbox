from __future__ import annotations

from dataclasses import dataclass

from cognitive_sandbox.simulation_test.scenario_probe import AnchorSimulationProbe


@dataclass(frozen=True)
class AgencyProbeCheckpoint:
    day: int
    event_count: int
    npc_action_count: int
    actions_by_character: tuple[tuple[str, int], ...]
    goal_changes: tuple[tuple[str, tuple[str, ...]], ...]
    thread_changes: int
    threads: tuple[tuple[str, str, float, float], ...]
    candidate_count: int
    knowledge_leaks: int


class AnchorAgencyProbe:
    """Compare autonomous agency at fresh Anchor Day 1, 7 and 30 checkpoints."""

    def __init__(self, probe=None):
        self.probe = probe or AnchorSimulationProbe()

    def run(self, *, random_seed=0, enable_player_idle=True):
        return self.probe.run(random_seed=random_seed, enable_player_idle=enable_player_idle)

    @staticmethod
    def compare(reports):
        reports = tuple(reports)
        return tuple(AgencyProbeCheckpoint(
            report.ticks,
            len(report.events),
            sum(summary.action_count for character_id, summary in report.characters.items()
                if character_id != "liangjing"),
            tuple(sorted((character_id, summary.action_count)
                         for character_id, summary in report.characters.items()
                         if character_id != "liangjing")),
            tuple(sorted((character_id, summary.goal_changes)
                         for character_id, summary in report.characters.items()
                         if summary.goal_changes)),
            len(report.thread_changes),
            tuple((thread.title, thread.status, thread.progress, thread.pressure)
                  for thread in report.thread_states),
            len(report.candidate_events),
            report.metrics.knowledge_leaks,
        ) for report in reports)
