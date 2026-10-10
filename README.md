# Cognitive Sandbox

A small, local-first desktop sandbox for exploring a world and its agents through a visual-novel style conversation. The MVP uses PySide6, SQLite, and an optional local Ollama model.

## Start

Requires Python 3.11 or newer.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m cognitive_sandbox.bootstrap
```

The app works without Ollama and shows a demo reply. To enable generation, set `COGNITIVE_SANDBOX_OLLAMA_MODEL` to an installed model name (for example `qwen2.5:7b`) and optionally `COGNITIVE_SANDBOX_OLLAMA_URL` (defaults to `http://localhost:11434`). Generation uses Ollama's local `/api/generate` endpoint.

Conversation events are stored in the platform's user data directory under `cognitive-sandbox/events.sqlite3`. The demo world is seeded on first launch.

## Checks

```powershell
python -m pytest
```

## Architecture

See [../architecture.md](../architecture.md). The core packages are separated by responsibility: `domain`, `application`, `infrastructure`, and `presentation`. UI code does not import database or HTTP adapters directly. The sprite renderer is an interface with a static image adapter; it can later be replaced by a Live2D-backed renderer.

## Current scope

One seeded world and agent, static portrait, dialogue history/input, a compact world/agent/memory inspector, and append-only SQLite events. No Live2D runtime or autonomous simulation loop in the MVP.
## Recreate the Windows environment after moving

The `.venv` directory is not portable and is intentionally excluded from project copies. From `D:\CognitiveSandbox`, create a fresh environment with the Python 3.12 runtime used for this project:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

If the packages are not available in the environment, install them only after access to the approved package source is available, or use provided local package files. The application and tests cannot run until PySide6 and pytest are installed. No network access or package installation is performed by the migration.

