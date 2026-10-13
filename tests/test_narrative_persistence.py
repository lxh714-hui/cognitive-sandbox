from dataclasses import replace

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.application.player_action_parser import PlayerActionParser
from cognitive_sandbox.character_presence import CharacterPresence, EntryRule, PresenceManager, PresenceState
from cognitive_sandbox.motivation import CharacterMotivation
from cognitive_sandbox.narrative.conflict_detector import Conflict
from cognitive_sandbox.narrative.event_planner import CandidateEvent
from cognitive_sandbox.narrative.narrative_anchor import NarrativeConstraint
from cognitive_sandbox.narrative.narrative_pressure import NarrativePressure
from cognitive_sandbox.narrative.narrative_state import NarrativeState
from cognitive_sandbox.narrative.narrative_thread import NarrativeThread, NarrativeThreadStatus
from cognitive_sandbox.persistence.models.save_metadata import SaveMetadata
from cognitive_sandbox.persistence.world_serializer import WorldSerializer


def test_narrative_runtime_round_trip_and_legacy_defaults():
    launcher = GameLauncher(action_interpreter=PlayerActionParser())
    session = launcher.start_scenario("example_world")
    session.presence_manager = PresenceManager(
        (CharacterPresence("doctor", "clinic", PresenceState.AVAILABLE, PresenceState.AVAILABLE),),
        (EntryRule("doctor", ("power_failure",), allowed_locations=("clinic",)),),
    )
    session.motivation_manager.set(CharacterMotivation("doctor", "救助幸存者", "寻找真相", "无法接受未知", "资源短缺"))
    thread = NarrativeThread("t1", "异常调查", ("doctor",), "信息冲突", .7, .2,
                             NarrativeThreadStatus.ACTIVE, ("goal:a", "goal:b"))
    candidate = CandidateEvent("c1", "information_lead_emerges", ("doctor",), "clinic", ("after:day1",), "由冲突产生", ("conflict1",), .6)
    session.narrative_state = NarrativeState((thread,), (candidate,), NarrativePressure(.5, .2, .4, "rising"))
    session.narrative_constraints = (NarrativeConstraint("doctor", "尽早出现", 2, ("must_follow_location_rules",)),)
    session.candidate_events = (candidate,)
    metadata = SaveMetadata(session.world_instance_id, session.executor.world_id, "example_world", "world", "desc", "d1", "d2")
    serializer = WorldSerializer()
    payload = serializer.serialize_world(metadata, session)
    decoded = serializer.deserialize_world(payload)
    narrative = decoded["narrative"]
    assert narrative["presence"] == session.presence_manager.presences
    assert narrative["motivations"] == session.motivation_manager.motivations
    assert narrative["state"] == session.narrative_state
    assert narrative["constraints"] == session.narrative_constraints
    assert narrative["candidates"] == (candidate,)

    legacy_payload = dict(payload)
    legacy_payload.pop("narrative")
    legacy = serializer.deserialize_world(legacy_payload)["narrative"]
    assert legacy["presence"] == ()
    assert legacy["motivations"] == ()
    assert legacy["state"] == NarrativeState()

    restored = launcher.restore_saved_world(decoded)
    assert restored.presence_manager.get("doctor").availability is PresenceState.AVAILABLE
    assert restored.motivation_manager.get("doctor").hidden_goal == "寻找真相"
    assert restored.narrative_state.threads == (thread,)


def test_motivation_views_do_not_expose_hidden_drives_by_default():
    motive = CharacterMotivation("liuyi", "调查异常", "寻找真相", "无法接受未知")
    assert motive.view_for("player").hidden_goal is None
    assert motive.view_for("liuyi").core_drive is None
    assert motive.view_for("system", privileged=True).hidden_goal == "寻找真相"
