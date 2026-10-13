from __future__ import annotations

from pathlib import Path


def scenario_package_directories(root: str | Path | None = None) -> tuple[Path, ...]:
    """Return package directories found beneath a data root; no scenario IDs are embedded here."""
    directory = Path(root) if root is not None else Path(__file__).resolve().parents[2] / "assets" / "scenarios"
    if not directory.is_dir():
        return ()
    return tuple(sorted(
        path for path in directory.iterdir()
        if path.is_dir() and (path / "scenario.json").is_file()
    ))
