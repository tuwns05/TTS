"""Tests for one-time VieNeu voice enrollment."""

from pathlib import Path

import numpy as np
import soundfile as sf

from vntts.services.voice_enrollment import VoiceEnrollmentService
from vntts.services.voice_profiles import VoiceProfileStore


class _FeatureEncoder:
    def __init__(self) -> None:
        self.temporary_path: Path | None = None

    def encode_voice_reference(
        self, engine_id: str, reference_audio_path: str
    ) -> tuple[np.ndarray, np.ndarray]:
        assert engine_id == "vieneu-v3"
        self.temporary_path = Path(reference_audio_path)
        assert self.temporary_path.is_file()
        assert sf.info(self.temporary_path).subtype == "PCM_16"
        return (
            np.array([0.25, -0.5], dtype=np.float32),
            np.array([[4, 5, 6]], dtype=np.int64),
        )


def test_enrollment_persists_features_and_discards_temporary_audio(tmp_path) -> None:
    source = tmp_path / "source.wav"
    sample_rate = 8_000
    timeline = np.arange(sample_rate * 6, dtype=np.float32) / sample_rate
    sf.write(source, 0.2 * np.sin(2 * np.pi * 180 * timeline), sample_rate)
    encoder = _FeatureEncoder()
    store = VoiceProfileStore(tmp_path / "data")
    service = VoiceEnrollmentService(encoder, store)  # type: ignore[arg-type]

    profile = service.enroll("Giọng của tôi", source)

    assert Path(profile.voice_artifact_path).is_file()
    assert encoder.temporary_path is not None
    assert not encoder.temporary_path.exists()
    assert list((tmp_path / "data" / "voice_profiles").rglob("*.wav")) == []
