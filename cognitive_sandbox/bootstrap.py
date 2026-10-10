from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from cognitive_sandbox.application.service import SandboxService
from cognitive_sandbox.domain.sample_world import SAMPLE_AGENT, SAMPLE_MEMORIES, SAMPLE_WORLD
from cognitive_sandbox.infrastructure.ollama import DemoProvider, OllamaProvider
from cognitive_sandbox.infrastructure.sqlite_store import SQLiteEventStore
from cognitive_sandbox.infrastructure.static_sprites import StaticSpriteRenderer
from cognitive_sandbox.presentation.main_window import MainWindow


def data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "cognitive-sandbox"


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Cognitive Sandbox")
    model = os.environ.get("COGNITIVE_SANDBOX_OLLAMA_MODEL", "").strip()
    base_url = os.environ.get("COGNITIVE_SANDBOX_OLLAMA_URL", "http://localhost:11434")
    provider = OllamaProvider(base_url, model) if model else DemoProvider()
    store = SQLiteEventStore(data_dir() / "events.sqlite3")
    service = SandboxService(store, provider)
    renderer = StaticSpriteRenderer(Path(__file__).parent / "assets" / "sprites")
    window = MainWindow(service, SAMPLE_WORLD, SAMPLE_AGENT, SAMPLE_MEMORIES, renderer)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
