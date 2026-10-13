from pathlib import Path


def test_pyinstaller_spec_packages_worlds_and_resources_without_tests():
    spec = (Path(__file__).resolve().parents[1] / "CognitiveSandbox.spec").read_text(encoding="utf-8")
    assert '"resources", "worlds", "characters", "configs"' in spec
    assert 'excluded_test_modules' in spec
    assert '"cognitive_sandbox.presentation.home.home_page"' in spec
