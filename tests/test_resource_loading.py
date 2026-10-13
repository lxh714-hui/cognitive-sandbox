from cognitive_sandbox.presentation.resource_manager import resource_path


def test_resource_paths_resolve_from_source_and_include_expected_folders():
    root = resource_path("assets", "scenarios", "anchor", "scenario.json")
    assert root.is_file()
    assert resource_path("resources", "icons").is_dir()
