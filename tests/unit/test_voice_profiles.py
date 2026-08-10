"""Tests for persistent local voice-cloning profiles."""

from pathlib import Path

from vntts.services.voice_profiles import VoiceProfileStore


def test_voice_profile_store_creates_renames_and_deletes(tmp_path) -> None:
    source = tmp_path / "sample.wav"
    source.write_bytes(b"RIFF-sample")
    store = VoiceProfileStore(tmp_path / "data")

    created = store.create("Giọng mẫu", source)
    renamed = store.rename(created.profile_id, "Giọng đã sửa")

    assert renamed.name == "Giọng đã sửa"
    assert renamed.status == "ready"
    assert store.list_profiles() == [renamed]
    copied_audio = renamed.reference_audio_path
    assert copied_audio != str(source)

    store.delete(created.profile_id)

    assert store.list_profiles() == []
    assert not Path(copied_audio).exists()
