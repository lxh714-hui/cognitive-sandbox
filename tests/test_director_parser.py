from cognitive_sandbox.director.constraint_type import ConstraintType
from cognitive_sandbox.director.constraint_target import ConstraintTarget
from cognitive_sandbox.director.director_intent import DirectorIntentParser


def test_parser_maps_prefer_avoid_forbid_and_knowledge_reveal_target():
    parser = DirectorIntentParser()
    assert parser.parse("我希望梁景和柳依依成为合作伙伴").constraint_type is ConstraintType.PREFER
    avoid = parser.parse("不要让梁景过早知道异常真相")
    assert avoid.constraint_type is ConstraintType.AVOID
    assert avoid.constraint_target is ConstraintTarget.KNOWLEDGE_REVEAL
    assert parser.parse("不要出现主角死亡").constraint_type is ConstraintType.FORBID
