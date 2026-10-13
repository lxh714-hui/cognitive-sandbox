from dataclasses import FrozenInstanceError
import json

import pytest

from cognitive_sandbox.application.ai_context_builder import AIContextBuilder
from cognitive_sandbox.application.character_mind_builder import CharacterMindBuilder
from cognitive_sandbox.application.json_character_loader import JsonCharacterLoader
from cognitive_sandbox.domain.character_card import CharacterCard, ExampleDialogue
from cognitive_sandbox.domain.character_mind import (
    CharacterMind,
    Identity,
    MemoryContext,
    PersonalityProfile,
    SpeechStyle,
)
from cognitive_sandbox.domain.constraint import Constraint


def _doctor_card(**kwargs):
    return CharacterCard(
        "doctor_internal_id",
        "林夏",
        occupation="医生",
        personality=("谨慎", "善良"),
        background="灾难前在急诊室工作。",
        goals=("救助幸存者",),
        constraints=(
            Constraint("soft", "优先保护患者"),
            Constraint("hard", "不会伤害无辜者"),
        ),
        **kwargs,
    )


def test_character_mind_creation_and_personality_context_generation():
    mind = CharacterMindBuilder().build(_doctor_card(), fears=("害怕失去患者",))
    context = AIContextBuilder().build(
        mind,
        current_scene={"location": "诊所大厅"},
        player_visible_information=("备用电源正在下降",),
    )

    assert mind.identity == Identity("林夏", "医生", "灾难前在急诊室工作。")
    assert context["personality"]["traits"] == ("谨慎", "善良")
    assert context["personality"]["values"] == ("优先保护患者",)
    assert context["personality"]["goals"] == ("救助幸存者",)
    assert context["personality"]["fears"] == ("害怕失去患者",)
    assert context["personality"]["taboos"] == ("不会伤害无辜者",)
    assert "doctor_internal_id" not in repr(context)


def test_speech_style_is_injected_into_ai_context():
    style = SpeechStyle(
        tone="平静",
        vocabulary=("医疗风险", "伤情"),
        sentence_style="先分析风险，再简短表达观点",
        preferred_phrases=("先别慌",),
        forbidden_styles=("突然热血化", "夸张口号"),
    )
    mind = CharacterMindBuilder().build(_doctor_card(), speech_style=style)
    context = AIContextBuilder().build(mind, current_scene={})

    assert context["speech_style"] == {
        "tone": "平静",
        "vocabulary": ("医疗风险", "伤情"),
        "sentence_style": "先分析风险，再简短表达观点",
        "preferred_phrases": ("先别慌",),
        "forbidden_styles": ("突然热血化", "夸张口号"),
    }
    assert "禁忌" in context["instructions"]
    assert "过去经历" in context["instructions"]


def test_stable_memory_is_immutable_and_memory_api_is_read_only():
    source = ["灾难前在急诊室工作。"]
    memory = MemoryContext(stable_memory=source)
    mind = CharacterMind(Identity("林夏", "医生"), PersonalityProfile(), memory_context=memory)
    source.append("外部改动")

    assert mind.get_character_memory().stable_memory == ("灾难前在急诊室工作。",)
    with pytest.raises(FrozenInstanceError):
        mind.memory_context = MemoryContext()
    with pytest.raises(TypeError):
        mind.get_character_memory().stable_memory[0] = "不可写入"


def test_character_card_json_loader_loads_example_dialogues(tmp_path):
    path = tmp_path / "character.json"
    path.write_text(
        json.dumps(
            {
                "character_id": "doctor",
                "name": "林夏",
                "identity": {"occupation": "医生"},
                "personality": ["谨慎"],
                "background": "在医院工作。",
                "goals": ["救助患者"],
                "constraints": [],
                "example_dialogues": [
                    {"user": "伤员情况如何？", "character": "先让我检查伤口。"}
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    card = JsonCharacterLoader().load(path)
    mind = CharacterMindBuilder().build(card)

    assert card.example_dialogues == (
        ExampleDialogue("伤员情况如何？", "先让我检查伤口。"),
    )
    assert mind.example_dialogues == card.example_dialogues
    context = AIContextBuilder().build(mind, current_scene={})
    assert context["example_dialogues"] == (
        {"user": "伤员情况如何？", "character": "先让我检查伤口。"},
    )


def test_ai_context_contains_only_explicit_scene_and_visible_information():
    mind = CharacterMindBuilder().build(_doctor_card())
    scene = {"location": "诊所", "visible_objects": ["灯光昏暗"]}
    context = AIContextBuilder().build(
        mind,
        current_scene=scene,
        player_visible_information=("听见远处警报",),
    )

    scene["visible_objects"].append("隐藏入口")
    assert context["current_scene"]["visible_objects"] == ("灯光昏暗",)
    assert context["player_visible_information"] == ("听见远处警报",)
    assert "world_state" not in context
    with pytest.raises(TypeError):
        context["identity"]["name"] = "被篡改"


