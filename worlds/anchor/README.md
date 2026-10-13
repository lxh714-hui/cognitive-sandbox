# 《锚点》

类型：Narrative Sandbox

一个关于异常、记忆与认知差异的小型模拟世界。这里没有预设结局；角色只依据各自获得的信息行动，异常线索的解释也可能不同。

## 启动

在桌面应用的“世界大厅”中选择“进入《锚点》”。也可以在 Python 中调用 `GameLauncher.start_anchor_world()`。

初始事件 `WorldInitialized` 仅作为世界启动记录，不会直接推进剧情或产生事件结果。

## 包结构

- `world_card.json`：世界规则与启动状态
- `characters/`：角色卡、认知倾向、初始情绪与权限配置
- `locations/`：地点与地点属性
- `knowledge/initial_knowledge.json`：按角色隔离的初始知识
- `narratives/initial_threads.json`：初始剧情线程状态
- `events/initial_events.json`：待运行系统使用的启动事件记录

角色卡存在不等于角色已登场。隐藏线索只进入对应角色的知识记录，不会作为全局 AI 上下文提供。
