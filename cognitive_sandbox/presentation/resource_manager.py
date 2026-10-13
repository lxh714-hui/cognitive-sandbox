from pathlib import Path
import sys


def resource_path(*parts):
    """Resolve bundled or source-tree assets without writing into the package."""
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return root.joinpath(*parts)
