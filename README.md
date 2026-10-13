# CognitiveSandbox

## English

**A local-first sandbox for interactive worlds and cognitive agents.**

CognitiveSandbox is a desktop application and simulation framework for building persistent worlds in which characters act from their own goals, knowledge, relationships, and the rules of the world. It is designed for open-ended roleplay and emergent stories: events and character choices shape what happens, rather than a fixed script determining the ending.

## Project position

The project combines world and scenario authoring with a playable simulation runtime. People define the world, its rules, the characters, and the boundaries of the simulation. AI can help draft content, interpret player input, and produce dialogue, while application and domain logic validate inputs and resolve state changes.

The current checkout includes both a small packaged example scenario and **《锚点》**, a larger narrative sandbox. They exercise different parts of the project and do not imply that every capability is equally mature or production-ready.

## Current capabilities

The following describes code and tests present in the current working tree:

- A PySide6 desktop app with world selection, roleplay, world management, story direction, and debugging views.
- Scenario packages and world, character, and event data, with loaders and validation. Generated world content follows a draft → validation → human confirmation → launch flow.
- A runtime for player actions and autonomous characters, including goals, routines, decision-making, and action resolution.
- Cognitive systems for observation, beliefs, emotion, memory, and character-specific knowledge. Information boundaries constrain what each character and the player can know.
- A Conflict System for persistent goal, information, relationship, resource, and value tensions. Conflicts shape candidate rankings and narrative possibilities; they do not select or force actions.
- World time, event history, relationships, and persistence. Incremental World Memory records event deltas and opportunity, conflict, decision, relationship, and World Tree history alongside the current snapshot.
- Narrative threads and opportunities that can emerge from simulation state, plus lazy World Tree branches that expand as choices are explored.
- Branch exploration and comparison, simulation tools, and views for inspecting world state and narrative history.
- AI adapters for supported generation, action interpretation, and dialogue workflows. AI output is treated as input to the application, not as authority to directly mutate the running world.

Feature presence in the working tree does not by itself guarantee release readiness. The repository currently contains substantial uncommitted work; see the Git status before treating this list as a released-version feature list.

## Architecture

```text
┌───────────────────────────────────────────────────┐
│ Presentation: PySide6 desktop UI                  │
│ world selection · roleplay · director · debug     │
└────────────────────────┬──────────────────────────┘
                         │ user actions and views
┌────────────────────────▼──────────────────────────┐
│ Application: use cases, orchestration, validation │◄─────┐
│ loading · actions · world creation · AI adapters  │      │
└────────────────────────┬──────────────────────────┘      │
                         │ validated commands and drafts   │
┌────────────────────────▼──────────────────────────┐      │
│ Domain and simulation: world rules · agents       │      │
│ goals · cognition · events · conflicts            │      │
│ relationships · agency · narrative opportunities  │      │
└────────────────────────┬──────────────────────────┘      │
                         │ state, decisions, history       │
┌────────────────────────▼──────────────────────────┐      │
│ Persistence and infrastructure: snapshots,        │      │
│ incremental World Memory, packages, settings,     │      │
│ and external service adapters                     │      │
└───────────────────────────────────────────────────┘      │
                                                           │
                            ┌──────────────────────────────┘
                            │ prompts / requests
                  ┌─────────▼──────────┐
                  │ AI providers       │
                  │ drafts / proposals │
                  └────────────────────┘
```

The presentation layer collects input and displays state. Application services coordinate workflows and connect adapters. Domain and simulation modules own world concepts, rules, decisions, and state transitions. Persistence and infrastructure support loading, saving, and external integrations. AI-assisted results pass through application validation and domain rules before they can affect a world.

## Design principles

- **People lead the project.** AI may assist implementation and content work; people own the architecture, design decisions, governance model, and final acceptance.
- **AI proposes; the runtime decides.** Generated content and interpreted actions are checked and constrained before they enter the simulation.
- **Authority and knowledge have boundaries.** A character's presence or an AI response does not grant access to hidden information or permission to change state.
- **World rules produce outcomes.** The runtime resolves actions and events against world state; narrative presentation describes those outcomes rather than replacing them.
- **World content is inspectable.** Scenarios use structured files and explicit validation so people can review what will enter a simulation.

## Roadmap

### Implemented in the current working tree

The systems summarized under [Current capabilities](#current-capabilities) are represented in the present source tree and tests. This status describes the working tree, not a claim that all changes have shipped in a release.

### Suggested next directions

There is no separate roadmap document in the repository. These are forward-looking directions for discussion, not committed delivery dates or release promises:

- Consolidate and document the growing module and service boundaries.
- Improve world-authoring workflows, validation feedback, and package documentation.
- Extend replay, simulation diagnostics, and tools for reviewing why a state change occurred.
- Continue evaluating long-run simulation quality, reliability, and performance.
- Make packaging and release procedures easier to reproduce and verify.

## Quick start

### Python development

Python 3.11 or newer is required. On Windows:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m cognitive_sandbox.presentation.app
```

The installed command-line entry point is `cognitive-sandbox`.

### Windows build

When using a packaged build, launch `CognitiveSandbox.exe` from the supplied `dist/CognitiveSandbox/` directory and keep its `_internal/` directory beside it.

## World packages and examples

A scenario package contains a scenario manifest, world definition, and character and event cards. The packaged sample is in [`assets/scenarios/example_world/`](assets/scenarios/example_world/). The **《锚点》** world is in [`worlds/anchor/`](worlds/anchor/); its README explains its data layout and startup flow.

## License

CognitiveSandbox is released under the MIT License. See [LICENSE](LICENSE).

## 中文版

**面向交互式世界与认知角色的本地优先模拟沙盒。**

CognitiveSandbox 是一款桌面应用与模拟框架，用于构建可持续运行的虚拟世界。角色依据自身目标、知识、关系和世界规则行动。系统面向开放式角色扮演与涌现叙事：世界事件和角色选择共同塑造后续发展，而不是由固定剧本预先决定结局。

## 项目定位

项目将世界与场景创作工具和可运行的模拟环境结合起来。创作者负责定义世界、规则、角色以及模拟边界。AI 可协助起草内容、理解玩家输入和生成对白；输入校验、规则判断与状态变化则由应用层和领域逻辑负责。

当前代码库包含一个结构较小的场景包，以及规模更大的叙事沙盒《锚点》。它们用于展示项目不同部分的能力，并不意味着所有功能都已达到相同的成熟度或可直接用于生产环境。

## 当前能力

以下内容概括了当前工作区中的代码与测试所体现的能力：

- 基于 PySide6 的桌面应用，提供世界选择、角色扮演、世界管理、叙事方向设置和调试视图。
- 支持场景包，以及世界、角色和事件数据的加载与校验。AI 生成的世界内容遵循“草稿 → 校验 → 人工确认 → 启动”的流程。
- 支持玩家行动和 NPC 自主运行，包括目标、日常行为、决策与行动解析。
- 提供观察、信念、情绪、记忆和角色专属知识等认知能力。信息边界限制每个角色及玩家能够获知的内容。
- 冲突系统（Conflict System）维护目标、信息、关系、资源和价值观之间持续存在的矛盾。冲突会影响候选方案的评估和叙事可能性，但不会替角色选择行动，也不会强迫行动发生。
- 支持世界时间、事件历史、角色关系和存档。增量式世界记忆（World Memory）在当前快照之外记录事件差异，以及机会、冲突、决策、关系和世界树的历史。
- 叙事线程与叙事机会（Opportunity）可以从模拟状态中涌现；世界树分支按需展开，随着选择逐步呈现。
- 提供分支探索与比较、模拟工具，以及用于检查世界状态和叙事历史的视图。
- AI 适配器支持内容生成、行动理解和对白等流程。AI 输出会交由应用流程处理，不具备直接修改运行中世界的权限。

工作区中存在某项功能，并不代表它已达到发布标准。仓库目前包含大量尚未提交的改动；在将上述内容视为正式发布版本的功能说明前，请先检查 Git 状态。

## 架构

```text
┌───────────────────────────────────────────────────┐
│ 表现层：PySide6 桌面界面                           │
│ 世界选择 · 角色扮演 · 导演模式 · 调试              │
└────────────────────────┬──────────────────────────┘
                         │ 玩家操作与界面展示
┌────────────────────────▼──────────────────────────┐
│ 应用层：用例编排、校验与流程协调                   │◄─────┐
│ 加载 · 行动 · 世界创建 · AI 适配器                 │      │
└────────────────────────┬──────────────────────────┘      │
                         │ 已校验的命令与草稿               │
┌────────────────────────▼──────────────────────────┐      │
│ 领域与模拟：世界规则 · 智能体                       │      │
│ 目标 · 认知 · 事件 · 冲突                           │      │
│ 关系 · 行动能动性（Agency）· 叙事机会               │      │
└────────────────────────┬──────────────────────────┘      │
                         │ 状态 · 决策 · 历史               │
┌────────────────────────▼──────────────────────────┐      │
│ 持久化与基础设施：快照、增量式世界记忆、             │      │
│ 场景包、设置和外部服务适配器                         │      │
└───────────────────────────────────────────────────┘      │
                                                           │
                            ┌──────────────────────────────┘
                            │ 提示词与请求
                  ┌─────────▼──────────┐
                  │ AI 提供方          │
                  │ 草稿与提案        │
                  └────────────────────┘
```

表现层负责收集输入并展示状态。应用服务协调具体流程并连接适配器。领域与模拟模块定义世界概念、规则、决策和状态转移。持久化与基础设施负责加载、保存及外部集成。AI 生成的结果必须先经过应用层校验和领域规则处理，才能影响世界。

## 设计原则

- **项目由人主导。** AI 可以协助实现和内容创作；架构、设计决策、治理方式与最终验收由人负责。
- **AI 提议，运行时裁定。** 生成内容和解析出的行动在进入模拟前都要经过检查与约束。
- **权限与知识各有边界。** 角色出现或 AI 生成回复，不代表其可以访问隐藏信息，也不代表它有权修改状态。
- **结果由世界规则决定。** 运行时依据世界状态处理行动与事件；叙事层负责表达结果，而不是取代结果裁定。
- **世界内容可检查。** 场景使用结构化文件和明确的校验流程，便于创作者审阅将要载入模拟的内容。

## 后续方向

### 当前工作区已实现

[当前能力](#当前能力)中概述的系统已在当前源码和测试中有所体现。这里描述的是工作区状态，不代表所有改动都已随正式版本发布。

### 可继续推进的方向

仓库目前没有单独的路线图文档。以下方向供后续讨论，不代表承诺的交付日期或发布计划：

- 梳理并记录逐渐扩展的模块与服务边界。
- 改善世界创作流程、校验反馈和场景包文档。
- 扩展回放、模拟诊断，以及分析状态变化原因的工具。
- 持续评估长时间模拟的质量、可靠性和性能。
- 让应用打包与发布流程更易于复现和验证。

## 快速开始

### Python 开发

需要 Python 3.11 或更新版本。Windows 环境可执行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m cognitive_sandbox.presentation.app
```

安装后也可以使用命令行入口：`cognitive-sandbox`。

### Windows 打包版本

运行打包版本时，请从提供的 `dist/CognitiveSandbox/` 目录启动 `CognitiveSandbox.exe`，并确保 `_internal/` 目录与可执行文件位于同一目录下。

## 世界包与示例

一个场景包由场景清单、世界定义、角色卡和事件卡组成。打包示例位于 [`assets/scenarios/example_world/`](assets/scenarios/example_world/)。《锚点》世界位于 [`worlds/anchor/`](worlds/anchor/)；其中的 README 介绍了数据结构和启动流程。

## 许可协议

CognitiveSandbox 采用 MIT License 发布，详见 [LICENSE](LICENSE)。

## 术语说明

- **提案（Proposal）**：对未来可能发展的候选建议，需要经过系统校验；它本身不是已经发生的事实。
- **机会（Opportunity）**：世界中值得关注、但尚待玩家或角色选择是否介入的叙事入口，不等同于任务或事件。
- **行动能动性（Agency）**：角色依据目标、认知、关系和当前状态评估并选择行动的能力；它不意味着行动必然发生。
- **冲突系统（Conflict System）**：维护持续矛盾并为行动评估和叙事发展提供背景的系统，不会直接替角色决策。
- **世界记忆（World Memory）**：在当前状态快照之外记录世界演变原因和历史变化的持久化信息。
- **叙事记忆（NarrativeMemory）**：用于表达与追踪叙事发展脉络的记忆概念；相关历史记录可与世界记忆及叙事回放配合使用。

## AI-Assisted Development Notice

AI coding tools have assisted with implementation, test support, documentation drafts, and architecture discussions. People lead the project: its architecture, design decisions, governance model, and final acceptance remain human-directed and human-reviewed. AI-generated changes are reviewed and validated before they are incorporated.

## AI 辅助开发声明

本项目在实现协助、测试支持、文档起草和架构讨论中使用了 AI 编程工具。项目愿景、架构决策、治理方式、验证和最终验收均由人主导并经人工审查。AI 生成的改动在纳入项目前都会经过审阅与验证。
