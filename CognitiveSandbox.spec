# PyInstaller onedir build for the desktop application.
from pathlib import Path

project_root = Path(SPECPATH).resolve()
datas = []
for resource_name in ("assets", "scenarios"):
    resource_dir = project_root / "cognitive_sandbox" / resource_name
    if resource_dir.is_dir():
        datas.append((str(resource_dir), f"cognitive_sandbox/{resource_name}"))

# User-facing scenario packages live at the repository-level assets directory.
scenario_packages = project_root / "assets" / "scenarios"
if scenario_packages.is_dir():
    datas.append((str(scenario_packages), "assets/scenarios"))

# Keep test suites out of the frozen application even if a future application
# module imports a test helper by mistake. The source tests remain untouched.
excluded_test_modules = {"pytest", "_pytest", "tests"}
ignored_source_dirs = {".git", ".venv", ".venv_backup", "build", "dist"}
for test_file in project_root.rglob("test_*.py"):
    relative = test_file.relative_to(project_root)
    if any(part in ignored_source_dirs for part in relative.parts):
        continue
    module_parts = list(relative.with_suffix("").parts)
    if module_parts[-1] == "__init__":
        module_parts.pop()
    if module_parts:
        excluded_test_modules.add(".".join(module_parts))

a = Analysis(
    [str(project_root / "cognitive_sandbox" / "presentation" / "app.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "cognitive_sandbox.presentation.app",
        "cognitive_sandbox.presentation.scenario_selection",
        "cognitive_sandbox.application.scenario_catalog",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=sorted(excluded_test_modules),
    noarchive=False,
    optimize=0,
)
# The build host's PATH may expose compatibility shims and unrelated ICU DLLs.
# These are Windows API-set contracts / host libraries and must resolve from
# Windows itself; bundling them can shadow the OS contracts used by QtCore.
a.binaries = [
    entry for entry in a.binaries
    if not Path(entry[0]).name.lower().startswith(("api-ms-win-", "icu"))
]
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CognitiveSandbox",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="CognitiveSandbox",
)
