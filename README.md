# Cognitive Sandbox

## An AI World Simulation Framework

Cognitive Sandbox is an AI-driven world simulation framework that allows users to create, simulate, and preserve persistent virtual worlds.

## Features

- AI-generated worlds from natural-language descriptions
- Structured World, Character, and Event models
- Autonomous agents with stateful decision and interaction flows
- Portable scenario packages
- Human-in-the-loop AI interaction
- Persistent world simulation data, including world events and conversation history

## Architecture

```text
World Document
      ↓
Character Cards
      ↓
Event Cards
      ↓
Scenario Runtime
      ↓
Simulation
      ↓
Narrative
```

World content is validated before it enters the runtime. AI can help create or interpret content, while the simulation remains responsible for world outcomes.

## Quick Start

### Windows executable

Run `CognitiveSandbox.exe` from the provided `dist/CognitiveSandbox/` folder. Keep the `_internal/` folder beside the executable; it contains the packaged runtime dependencies. The application opens the scenario selection flow on startup.

### Python development

Use Python 3.12 on Windows:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m cognitive_sandbox.presentation.app
```

Run the test suite with:

```powershell
python -m pytest -q
```

## AI World Creation

```text
Describe a world
       ↓
AI generates a world package draft
       ↓
Validation
       ↓
Human confirmation
       ↓
Start the world
```

Generated content is a draft. It must pass validation and be confirmed before it can be used to start a runtime; the AI does not directly create or change the running world state.

## World Package Format

A scenario package contains:

```text
scenario.json
world.json
characters/
events/
```

`scenario.json` describes the package, `world.json` defines the setting and rules, and the `characters/` and `events/` directories contain individual character and event cards.

## Example World

**《灰港纪元》** is a small playable example set in a post-disaster harbor city. Energy is scarce, survivors have formed settlements, and people must cooperate with incomplete information. Its initial event cards establish context and conditions; they do not prescribe a fixed story outcome.

The package is in [`assets/scenarios/example_world/`](assets/scenarios/example_world/).

## Roadmap

### Completed

- [x] AI World Generation
- [x] Character Cards
- [x] Event Cards
- [x] Scenario Packages
- [x] Example World

### Planned

- [ ] Memory System
- [ ] Timeline Save/Load
- [ ] World Chronicle
- [ ] Character Portrait System
- [ ] Relationship Simulation

## License

Cognitive Sandbox is released under the MIT License. See [LICENSE](LICENSE).

## AI-Assisted Development Notice

AI coding tools were used for:

- implementation assistance
- testing support
- documentation drafting
- architecture discussion

Project vision, architecture decisions, validation, and final acceptance remain human-directed and human-reviewed. AI-generated changes are reviewed and validated before incorporation.
