from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class UserDataPaths:
    root: Path
    settings: Path
    savegames: Path
    logs: Path


def initialize_user_data(root=None):
    base = Path(root) if root is not None else Path(os.environ.get("LOCALAPPDATA", Path.home())) / "CognitiveSandbox" / "user_data"
    paths = UserDataPaths(base, base / "settings", base / "savegames", base / "logs")
    for path in (paths.settings, paths.savegames, paths.logs):
        path.mkdir(parents=True, exist_ok=True)
    return paths
