from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.application.player_action_parser import PlayerActionParser
from cognitive_sandbox.application.world_evolution_manager import WorldEvolutionManager
from cognitive_sandbox.domain.character_card import CharacterCard
from cognitive_sandbox.domain.event_card import EventCard
from cognitive_sandbox.domain.patch_validation_result import PatchValidationStatus
from cognitive_sandbox.domain.world_patch import CharacterAddition, WorldPatch, WorldPatchType


def _character_patch(card_id="wandering_trader", **overrides):
    introduction_method = overrides.pop(
        "introduction_method", "收到求救信号后抵达医疗中心"
    )
    appearance_condition = overrides.pop("appearance_condition", "当前世界发出求救信号后")
    entry_event = overrides.pop("entry_event", "一名商人抵达医疗中心")
    payload = CharacterAddition(
        character_card=CharacterCard(
            character_id=card_id,
            name="流浪商人",
            occupation="商人",
            background="从当前时间点起加入港区聚落。",
        ),
        introduction_method=introduction_method,
        appearance_condition=appearance_condition,
        entry_event=entry_event,
    )
    fields = dict(
        id="patch_trader",
        type=WorldPatchType.CHARACTER_ADDITION,
        title="加入角色：流浪商人",
        description="加入一名流浪商人",
        created_at="now",
        effective_time="当前",
        source="user_confirmed_draft",
        payload=payload,
    )
    fields.update(overrides)
    return WorldPatch(**fields)


def _session():
    return GameLauncher(action_interpreter=PlayerActionParser()).start_scenario("example_world")


def test_character_patch_is_added_without_modifying_world_history_or_state():
    library_session = _session()
    from cognitive_sandbox.application.world_library import WorldLibrary

    library = WorldLibrary()
    world = library.register(library_session)
    manager = WorldEvolutionManager(library)
    patch = _character_patch()
    original_state = dict(library_session.world_state)
    original_history = library_session.scenario_content.world_document.history

    result = manager.apply(world.instance_id, patch, confirmed=True)

    assert result.status is PatchValidationStatus.SUCCESS
    assert library.patches_for(world.instance_id) == (patch,)
    assert library_session.world_state == original_state
    assert library_session.scenario_content.world_document.history == original_history


def test_duplicate_character_id_is_rejected_without_appending_patch():
    from cognitive_sandbox.application.world_library import WorldLibrary

    library = WorldLibrary()
    world = library.register(_session())
    manager = WorldEvolutionManager(library)
    patch = _character_patch("doctor")

    result = manager.apply(world.instance_id, patch, confirmed=True)

    assert result.status is PatchValidationStatus.REJECTED
    assert "已存在" in result.reasons[0]
    assert library.patches_for(world.instance_id) == ()


def test_temporal_conflict_rejects_retroactive_character_presence():
    from cognitive_sandbox.application.world_library import WorldLibrary
    from cognitive_sandbox.domain.scenario_content import ScenarioContent
    from cognitive_sandbox.domain.world_document import WorldDocument

    session = _session()
    content = ScenarioContent(
        scenario=session.scenario,
        world_document=WorldDocument(
            "w", "测试世界", "描述", history=("第5天医疗中心废弃",)
        ),
        character_cards=(),
    )
    session.scenario_content = content
    session.world_state["current_day"] = 10
    library = WorldLibrary()
    world = library.register(session)
    patch = _character_patch(
        introduction_method="林博士第1天起一直住在医疗中心",
        appearance_condition="第1天",
    )

    result = WorldEvolutionManager(library).apply(world.instance_id, patch, confirmed=True)

    assert result.status is PatchValidationStatus.REJECTED
    assert library.patches_for(world.instance_id) == ()


def test_character_fact_conflict_with_non_magic_world_is_rejected():
    from cognitive_sandbox.application.world_library import WorldLibrary
    from cognitive_sandbox.domain.scenario_content import ScenarioContent
    from cognitive_sandbox.domain.world_document import WorldDocument

    session = _session()
    session.scenario_content = ScenarioContent(
        scenario=session.scenario,
        world_document=WorldDocument("w", "测试世界", "描述", rules=("世界不存在魔法。",)),
    )
    library = WorldLibrary()
    world = library.register(session)
    card = CharacterCard("mage", "法师", occupation="魔法师")
    payload = CharacterAddition(card, "从当前时间点引入", "现在", "法师抵达")
    patch = WorldPatch(
        id="mage_patch", type=WorldPatchType.CHARACTER_ADDITION,
        title="加入法师", description="加入法师", created_at="now",
        effective_time="当前", source="user", payload=payload,
    )

    result = WorldEvolutionManager(library).validate(world.instance_id, patch)
    assert result.status is PatchValidationStatus.REJECTED
    assert library.patches_for(world.instance_id) == ()


def test_lore_patch_requires_confirmation_and_then_is_added():
    from cognitive_sandbox.application.world_library import WorldLibrary

    library = WorldLibrary()
    world = library.register(_session())
    patch = WorldPatch(
        id="lore_1",
        type=WorldPatchType.LORE_PATCH,
        title="新增设定",
        description="港区有一条新的地下通道",
        created_at="now",
        effective_time="当前",
        source="user draft",
        payload="港区存在一条此前未被发现的地下通道。",
    )
    manager = WorldEvolutionManager(library)

    pending = manager.apply(world.instance_id, patch)
    assert pending.status is PatchValidationStatus.NEEDS_CONFIRMATION
    assert library.patches_for(world.instance_id) == ()

    confirmed = manager.apply(world.instance_id, patch, confirmed=True)
    assert confirmed.status is PatchValidationStatus.SUCCESS
    assert library.patches_for(world.instance_id) == (patch,)


def test_event_addition_is_stored_as_future_patch_not_executed():
    from cognitive_sandbox.application.world_library import WorldLibrary

    library = WorldLibrary()
    session = _session()
    session.world_state["current_day"] = 5
    world = library.register(session)
    patch = WorldPatch(
        id="event_patch", type=WorldPatchType.EVENT_ADDITION,
        title="后续事件", description="一条待触发的事件", created_at="now",
        effective_time="第6天或之后", source="user",
        payload=EventCard("event_future", "求救信号", "有人发出信号", "future", conditions=("第6天",)),
    )
    before = dict(session.world_state)

    result = WorldEvolutionManager(library).apply(world.instance_id, patch, confirmed=True)

    assert result.status is PatchValidationStatus.SUCCESS
    assert library.patches_for(world.instance_id) == (patch,)
    assert session.world_state == before


def test_patch_models_are_immutable():
    patch = _character_patch()
    with pytest.raises(FrozenInstanceError):
        patch.title = "改写历史"
    with pytest.raises(FrozenInstanceError):
        patch.payload.introduction_method = "从前就住在这里"
