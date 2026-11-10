from deskrecordor.config.settings import Settings


def test_settings_round_trip(tmp_path):
    settings = Settings(output_dir=str(tmp_path / "videos"), default_microphone="mic-1", final_format="mp4")
    path = tmp_path / "settings.json"
    settings.save(path)
    loaded = Settings.load(path)
    assert loaded.default_microphone == "mic-1"
    assert loaded.output_dir == str(tmp_path / "videos")
    assert loaded.final_format == "mp4"


def test_default_settings_are_created(tmp_path):
    settings = Settings.default()
    assert settings.final_format == "mp4"
    assert settings.video_quality == "balanced"
    assert "DeskRecordor" in settings.output_dir
