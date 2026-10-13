from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.director.director_constraint import DirectorConstraintStatus
from cognitive_sandbox.director.director_intent import DirectorIntent, DirectorIntentType


def test_anchor_director_goal_uses_causal_path_without_creating_world_event():
    session = GameLauncher().start_world("anchor")
    before = dict(session.world_state)
    result = session.director_manager.submit_intent(DirectorIntent(
        DirectorIntentType.CHARACTER_ENTRY, "liuyiyi", "希望柳依依早点出现"
    ))
    assert result.constraint.status in {DirectorConstraintStatus.SEARCHING, DirectorConstraintStatus.BLOCKED}
    assert result.paths
    assert all("no_teleportation" in path.conditions or "character_agency_preserved" in path.conditions
               for path in result.paths)
    assert not session.executor.event_timeline.events
    assert dict(session.world_state) == before
