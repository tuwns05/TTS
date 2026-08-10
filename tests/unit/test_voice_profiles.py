"""Tests for persistent local voice-cloning profiles."""

from pathlib import Path

import numpy as np
import soundfile as sf

from vntts.services.voice_profiles import VoiceProfileStore


def test_voice_profile_store_creates_renames_and_deletes(tmp_path) -> None:
    source = tmp_path / "sample.wav"
    sample_rate = 8_000
    timeline = np.arange(sample_rate * 6, dtype=np.float32) / sample_rate
    sf.write(source, 0.2 * np.sin(2 * np.pi * 180 * timeline), sample_rate)
    store = VoiceProfileStore(tmp_path / "data")

    created = store.create("Giọng mẫu", source)
    renamed = store.rename(created.profile_id, "Giọng đã sửa")

    assert renamed.name == "Giọng đã sửa"
    assert renamed.status == "ready"
    assert renamed.warnings == ()
    assert store.list_profiles() == [renamed]
    copied_audio = renamed.reference_audio_path
    assert copied_audio != str(source)
    assert Path(copied_audio).suffix == ".wav"
    assert sf.info(copied_audio).subtype == "PCM_16"

    store.delete(created.profile_id)

    assert store.list_profiles() == []
    assert not Path(copied_audio).exists()
