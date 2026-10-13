from __future__ import annotations

from datetime import datetime, timezone

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.character_presence.entry_rule import EntryRule
from cognitive_sandbox.domain.world_instance import WorldInstance
from cognitive_sandbox.simulation_test.simulation_runner import SimulationRunner


class AnchorSimulationProbe:
    """Run fresh Anchor instances at cumulative Day 1, Day 7 and Day 30 checkpoints."""

    CHECKPOINTS = (1, 7, 30)

    def __init__(self, launcher=None, runner=None):
        self.launcher = launcher or GameLauncher()
        self.runner = runner or SimulationRunner()

    def run(self, *, random_seed: int = 0, enable_player_idle: bool = True):
        reports = []
        for ordinal, day in enumerate(self.CHECKPOINTS):
            session = self.launcher.start_anchor_world()
            session.executor.world_clock.restore(datetime(2026, 1, 1, 20, tzinfo=timezone.utc).isoformat())
            self._configure_probe(session)
            instance = WorldInstance(
                session.world_instance_id, "anchor_world", session.world_instance_id,
                "锚点", "Phase 10 离线模拟探针实例。", "active", "running",
                session.executor.world_clock.current_time().isoformat(), "liangjing",
            )
            reports.append(self.runner.run(
                instance, session=session, tick_count=day,
                random_seed=random_seed + ordinal, enable_player_idle=enable_player_idle,
                on_start=self._trigger_probe_clue,
            ))
        return tuple(reports)

    @staticmethod
    def _configure_probe(session):
        """Add explicit test stimuli/goals to the disposable probe runtime only.

        This makes a known clue available through the normal presence rule. It
        does not add or replace a character goal, and is confined to each fresh
        probe runtime.
        """
        session.presence_manager.add_rule(EntryRule(
            "liuyiyi", trigger_event_types=("anomaly_detected",),
            allowed_locations=("neighborhood",),
        ))

    @staticmethod
    def _trigger_probe_clue(session, context):
        from cognitive_sandbox.domain.world_events import WorldEvent

        now = session.executor.world_clock.current_time().isoformat()
        event = WorldEvent(
            f"probe_anomaly_{session.world_instance_id}", "main", session.executor.world_id,
            "anomaly_detected", "system",
            {"description": "探针刺激：街区出现一条尚待核实的异常线索。", "importance": .5},
            0, target_id="liuyiyi", location="neighborhood", timestamp=now,
        )
        session.executor.event_pipeline.publish(event, context=context)
        witnessed = WorldEvent(
            f"probe_liang_observed_{session.world_instance_id}", "main", session.executor.world_id,
            "anomaly_observed", "liangjing",
            {"description": "梁景亲眼发现一条与街区钟表记录有关的异常线索。", "importance": .65},
            0, location="liangjing_home", timestamp=now,
        )
        session.executor.event_pipeline.publish(witnessed, context=context)
        available = session.presence_manager.evaluate_entry(
            "liuyiyi", event_type=event.event_type, current_location=event.location,
            current_time=now,
        )
        if available.availability.value == "AVAILABLE":
            session.presence_manager.introduce("liuyiyi", current_location=event.location)


def main():
    for report in AnchorSimulationProbe().run():
        print(
            f"Day {report.ticks}: {report.world_name} | "
            f"time={report.start_time} → {report.end_time} | "
            f"events={len(report.events)} | state_changes={len(report.state_changes)} | "
            f"activity={report.metrics.activity_rate:.3f} | "
            f"NPC_independence={report.metrics.character_independence:.3f} | "
            f"emotion={report.metrics.emotion_dynamics:.3f} | "
            f"knowledge_leaks={report.metrics.knowledge_leaks} | "
            f"thread_changes={len(report.thread_changes)} | "
            f"candidates={len(report.candidate_events)} | "
            f"social_encounters={len(report.encounters)}"
        )
        for change in report.state_changes:
            print(f"  state {change.target_type}.{change.target_id}.{change.field}: "
                  f"{change.old_value} → {change.new_value} ({change.reason})")
        for character_id, summary in report.characters.items():
            print(
                f"  {character_id}: actions={summary.action_count}, "
                f"emotion_changes={len(summary.emotion_changes)}, "
                f"cognitive_interpretations={len(summary.cognition_changes)}"
            )
            if summary.cognition_changes:
                print(f"    latest interpretation: {summary.cognition_changes[-1].interpretation}")
        for thread in report.thread_states:
            print(f"  thread {thread.title}: {thread.status}, progress={thread.progress:.2f}")
        for transition in report.relationship_transitions:
            print(f"  relationship {transition.character_a} → {transition.character_b}: "
                  f"{transition.previous_stage.value} → {transition.new_stage.value} "
                  f"(source={transition.source_event_id})")
        anchor_pair = next((item for item in report.relationship_stages
                            if (item.character_a, item.character_b) == ("liangjing", "liuyiyi")), None)
        if anchor_pair is not None:
            print(f"  Anchor relationship liangjing → liuyiyi: {anchor_pair.stage.value}")
        pair_encounters = [item for item in report.encounters
                           if {item.character_a, item.character_b} == {"liangjing", "liuyiyi"}]
        print(f"  Anchor Liang-Jade encounters in this interval: {len(pair_encounters)}")
        for constraint in report.director_constraints:
            status = getattr(getattr(constraint, "status", None), "value", "PENDING")
            print(f"  director constraint: {status} · {constraint.target or 'world'} · {constraint.intent.description}")


if __name__ == "__main__":
    main()

