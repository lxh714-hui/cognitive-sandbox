from __future__ import annotations

from dataclasses import replace

from cognitive_sandbox.narrative.event_planner import CandidateEvent
from cognitive_sandbox.narrative.narrative_pressure import NarrativePressure
from cognitive_sandbox.narrative.narrative_thread import NarrativeThreadStatus
from cognitive_sandbox.narrative.narrative_state import NarrativeState


class AgencyNarrativeTracker:
    """Accumulate goal-related NPC activity as thread pressure and conditional candidates."""

    _THREAD_ACTIONS = {"npc_investigated", "npc_observed", "npc_organized", "npc_socialized"}

    def apply(self, state: NarrativeState, event):
        if not isinstance(state, NarrativeState) or event.event_type not in self._THREAD_ACTIONS:
            return state
        actor_id = event.actor_id
        action_text = " ".join((event.event_type, str(event.payload.get("action_type", "")),
                                 str(event.payload.get("reason", "")),
                                 str(event.payload.get("parameters", {}).get("topic", "")
                                     if isinstance(event.payload.get("parameters", {}), dict) else ""))).casefold()
        threads = list(state.threads)
        updated_ids = set()
        for index, thread in enumerate(threads):
            if actor_id not in thread.participants or thread.status in {
                NarrativeThreadStatus.RESOLVED, NarrativeThreadStatus.FAILED,
            }:
                continue
            thread_text = f"{thread.title} {thread.conflict}".casefold()
            if event.event_type in {"npc_investigated", "npc_organized"}:
                if not any(token in thread_text for token in ("调查", "异常", "线索", "investigat", "mystery")):
                    continue
            elif event.event_type == "npc_socialized":
                if "线索" in action_text or "异常" in action_text:
                    if not any(token in thread_text for token in ("调查", "异常", "线索", "investigat")):
                        continue
                elif not any(token in thread_text for token in ("交汇", "相遇", "关系", "social", "meeting")):
                    continue
            elif event.event_type == "npc_observed":
                if not any(token in thread_text for token in ("调查", "异常", "观察", "生活", "investigat")):
                    continue
            # Thread progress is evidence of accumulated character activity, not a
            # forced plot outcome. Updates are bounded and produce candidates only.
            progress = min(1.0, thread.progress + .04)
            pressure = min(1.0, thread.pressure + .06)
            status = thread.status
            if status in {NarrativeThreadStatus.DORMANT, NarrativeThreadStatus.POSSIBLE}:
                status = NarrativeThreadStatus.ACTIVE
            if pressure >= .6:
                status = NarrativeThreadStatus.ESCALATING
            threads[index] = replace(thread, progress=progress, pressure=pressure, status=status)
            updated_ids.add(thread.id)
        if not updated_ids:
            return state
        candidates = list(state.candidates)
        for thread in threads:
            if thread.id not in updated_ids or thread.pressure < .24:
                continue
            candidate_id = f"agency:{thread.id}"
            candidate = CandidateEvent(
                candidate_id, "thread_pressure_opportunity", thread.participants,
                event.location, ("conditions_must_be_verified", "no_forced_outcome"),
                f"角色围绕「{thread.title}」的主动行动积累了推进机会。",
                (thread.id,), thread.pressure,
            )
            index = next((index for index, item in enumerate(candidates)
                          if getattr(item, "candidate_id", None) == candidate_id), None)
            if index is None:
                candidates.append(candidate)
            else:
                candidates[index] = candidate
        old = state.pressure or NarrativePressure()
        peak = max((thread.pressure for thread in threads if thread.id in updated_ids), default=0)
        pressure = NarrativePressure(
            max(old.urgency, peak), old.danger, max(old.unresolved_degree, peak),
            "rising" if peak > old.urgency + .03 else old.trend, old.goal_stagnation,
            old.conflict_pressure,
        )
        return NarrativeState(tuple(threads), tuple(candidates), pressure)
