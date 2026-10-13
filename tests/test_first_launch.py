from cognitive_sandbox.application.first_launch import initialize_user_data


def test_first_launch_creates_user_data_outside_source_tree(tmp_path):
    paths = initialize_user_data(tmp_path / "user_data")
    assert paths.settings.is_dir() and paths.savegames.is_dir() and paths.logs.is_dir()
    assert paths.root == tmp_path / "user_data"
