from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.director import DirectorConstraintStatus


def test_director_manager_finds_causal_entry_and_meeting_routes_without_world_events():
    session = GameLauncher().start_scenario("example_world")
    result = session.director_manager.submit_text("希望医生早点出现")
    assert result.accepted
    assert result.constraint.status is DirectorConstraintStatus.SEARCHING
    assert result.paths
    assert all("teleport" in " ".join(path.conditions) or "causal" in " ".join(path.conditions)
               or path.title for path in result.paths)
    assert session.director_constraints
    assert session.candidate_events
    assert not session.executor.event_timeline.events
    assert all("直接修改" not in path.rationale for path in result.paths)


def test_meeting_paths_respect_separate_character_locations():
    from cognitive_sandbox.director.director_intent import DirectorIntent, DirectorIntentType
    from cognitive_sandbox.director.director_path_finder import DirectorPathFinder
    from cognitive_sandbox.character_presence.character_presence import CharacterPresence, PresenceState

    intent = DirectorIntent(DirectorIntentType.CHARACTER_MEETING, "a,b", "让两人相遇")
    paths = DirectorPathFinder().find_paths(
        intent, presences=(CharacterPresence("a", "north", PresenceState.ACTIVE, PresenceState.ACTIVE),
                           CharacterPresence("b", "south", PresenceState.ACTIVE, PresenceState.ACTIVE))
    )
    assert "causal_travel_required" in paths[0].conditions
    assert "前往可达地点" in "".join(paths[0].steps)
