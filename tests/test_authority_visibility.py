from cognitive_sandbox.authority import AuthorityManager, CharacterAuthority


def test_character_and_director_visibility_scopes_do_not_reveal_hidden_state():
    manager = AuthorityManager(
        (CharacterAuthority.player("player"), CharacterAuthority.important_character("doctor")),
        player_character_id="player",
    )
    assert manager.check_visibility_permission("doctor", "doctor", "true_emotion")
    assert manager.check_visibility_permission("player", "doctor", "public_status")
    assert not manager.check_visibility_permission("player", "doctor", "hidden_knowledge")
    assert not manager.check_visibility_permission("director", "doctor", "hidden_motivation")
    from cognitive_sandbox.authority import AuthorityLevel
    assert manager.check_visibility_permission(
        "debug", "doctor", "hidden_knowledge", requester_level=AuthorityLevel.DEBUG
    )
    context = manager.ai_authority_context("doctor")
    assert context["character_id"] == "doctor"
    assert "complete_world_state" in context["excluded_information"]
    assert "true_emotion" not in context["allowed_information"]
    assert "self_emotion" in context["allowed_information"]


def test_ai_character_requests_carry_only_the_speaker_authority_projection():
    from cognitive_sandbox.application.game_launcher import GameLauncher
    from cognitive_sandbox.application.ai_gm_adapter import AIGMAdapter
    from cognitive_sandbox.domain.ai_gm import AIGMResponse

    class CaptureProvider:
        def __init__(self):
            self.request = None

        def complete(self, request):
            self.request = request
            return AIGMResponse("……")

    session = GameLauncher().start_scenario("example_world")
    doctor = next(item for item in session.agent_contexts if item.character_id == "doctor")
    player = session.agent_context
    provider = CaptureProvider()
    adapter = AIGMAdapter(provider)
    adapter.generate_dialogue(
        doctor, player, "你好",
        character_mind=session.executor.character_minds[doctor.character_id],
        authority_context=session.authority_manager.ai_authority_context(doctor.character_id),
    )
    context = provider.request.context
    assert context["speaker"]["authority_context"]["character_id"] == "doctor"
    assert "complete_world_state" in context["speaker"]["authority_context"]["excluded_information"]
    assert "world_state" not in context["speaker"]
