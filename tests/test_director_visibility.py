from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.knowledge.models.world_fact import WorldFact


def test_director_paths_do_not_read_or_echo_hidden_knowledge():
    session = GameLauncher().start_scenario("example_world")
    secret = "secret_vault_location_xyz"
    session.knowledge_store.add_fact(WorldFact("hidden", secret, "secret", "day-1", (), 1.0))
    result = session.director_manager.submit_text("增加异常线索")
    rendered = repr((result, session.candidate_events))
    assert secret not in rendered
    assert "knowledge" not in " ".join(path.rationale.casefold() for path in result.paths)
