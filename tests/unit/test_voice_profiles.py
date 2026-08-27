"""Tests for persistent local voice-cloning profiles."""

from pathlib import Path

import numpy as np

from vntts.services.voice_profiles import VoiceProfileStore


def test_voice_profile_store_creates_renames_and_deletes(tmp_path) -> None:
    store = VoiceProfileStore(tmp_path / "data")
    speaker_emb = np.array([0.1, -0.2, 0.3], dtype=np.float32)
    ref_codes = np.array([[1, 2, 3]], dtype=np.int64)

    created = store.create("Giọng mẫu", speaker_emb, ref_codes)
    renamed = store.rename(created.profile_id, "Giọng đã sửa")

    assert renamed.name == "Giọng đã sửa"
    assert renamed.status == "ready"
    assert renamed.warnings == ()
    assert store.list_profiles() == [renamed]
    artifact_path = renamed.voice_artifact_path
    assert Path(artifact_path).suffix == ".npz"
    assert list((tmp_path / "data" / "voice_profiles").rglob("*.wav")) == []
    with np.load(artifact_path, allow_pickle=False) as artifact:
        np.testing.assert_allclose(artifact["speaker_emb"], speaker_emb)
        np.testing.assert_array_equal(artifact["ref_codes"], ref_codes)

    store.delete(created.profile_id)

    assert store.list_profiles() == []
    assert not Path(artifact_path).exists()
