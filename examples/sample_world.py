from cognitive_sandbox.domain.models import Agent, CognitiveMemory, World

SAMPLE_WORLD = World(
    id="harbor-at-dusk",
    name="暮港来信",
    description="一座靠潮汐与旧信件记住时间的海边小城。",
    facts=("现在是初秋傍晚", "旧灯塔将在今晚重新点亮", "海风里有淡淡的桂花香"),
)

SAMPLE_AGENT = Agent(
    id="lin-xia",
    world_id=SAMPLE_WORLD.id,
    name="林夏",
    role="灯塔管理员的女儿",
    persona="安静、敏锐，喜欢收集没有寄出的信。",
    sprite_key="lin-xia",
)

SAMPLE_MEMORIES = (
    CognitiveMemory("memory-1", SAMPLE_AGENT.id, "小时候曾和父亲一起点亮灯塔。"),
    CognitiveMemory("memory-2", SAMPLE_AGENT.id, "她还没有告诉任何人，今天收到一封旧信。"),
)
