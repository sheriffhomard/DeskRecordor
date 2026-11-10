from deskrecordor.utils.file_manager import ensure_unique_path, generate_output_filename


def test_generate_filename_uses_timestamp_pattern():
    name = generate_output_filename(prefix="deskrecordor")
    assert name.endswith("_deskrecordor.mp4")
    assert len(name) > 20


def test_unique_path_avoids_conflicts(tmp_path):
    path = tmp_path / "recording.mp4"
    path.write_text("done")
    unique = ensure_unique_path(path)
    assert unique.name.startswith("recording_1")
