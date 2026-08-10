"""Tests for voice-cloning reference audio preprocessing."""

import numpy as np
import pytest
import soundfile as sf

from vntts.services.audio_processor import TARGET_PEAK, preprocess_reference_audio
from vntts.utils.exceptions import ValidationError


SAMPLE_RATE = 8_000


def _tone(duration: float, amplitude: float = 0.25) -> np.ndarray:
    timeline = np.arange(round(SAMPLE_RATE * duration), dtype=np.float32) / SAMPLE_RATE
    return np.asarray(amplitude * np.sin(2 * np.pi * 180 * timeline), dtype=np.float32)


def _write(path, audio: np.ndarray) -> None:  # type: ignore[no-untyped-def]
    sf.write(path, audio, SAMPLE_RATE, format="WAV", subtype="FLOAT")


def test_corrupt_reference_audio_is_rejected(tmp_path) -> None:
    source = tmp_path / "broken.wav"
    source.write_bytes(b"not-a-real-audio-file")

    with pytest.raises(ValidationError, match="Không thể giải mã"):
        preprocess_reference_audio(source)


def test_silent_reference_audio_is_rejected(tmp_path) -> None:
    source = tmp_path / "silence.wav"
    _write(source, np.zeros(SAMPLE_RATE * 6, dtype=np.float32))

    with pytest.raises(ValidationError, match="không chứa phần có tiếng"):
        preprocess_reference_audio(source)


def test_reference_with_less_than_six_seconds_of_voice_is_rejected(tmp_path) -> None:
    source = tmp_path / "short.wav"
    _write(source, _tone(5.5))

    with pytest.raises(ValidationError, match="ít nhất 6 giây"):
        preprocess_reference_audio(source)


def test_normal_reference_audio_has_no_warnings(tmp_path) -> None:
    source = tmp_path / "normal.wav"
    stereo = np.column_stack((_tone(6.0) + 0.04, _tone(6.0) + 0.02))
    _write(source, stereo)

    result = preprocess_reference_audio(source)

    assert result.warnings == ()
    assert result.duration_seconds == pytest.approx(6.0)
    assert result.audio.ndim == 1
    assert float(np.mean(result.audio)) == pytest.approx(0.0, abs=1e-6)
    assert float(np.max(np.abs(result.audio))) == pytest.approx(TARGET_PEAK, rel=1e-5)


def test_reference_longer_than_engine_limit_has_warning(tmp_path) -> None:
    source = tmp_path / "long.wav"
    _write(source, _tone(9.0))

    result = preprocess_reference_audio(source)

    assert any("8 giây" in warning for warning in result.warnings)


def test_clipped_reference_audio_has_warning(tmp_path) -> None:
    source = tmp_path / "clipped.wav"
    clipped = np.where(np.arange(SAMPLE_RATE * 6) % 2, 1.0, -1.0).astype(np.float32)
    _write(source, clipped)

    result = preprocess_reference_audio(source)

    assert any("clipping" in warning for warning in result.warnings)
