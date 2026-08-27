"""Validation and light normalization for voice-cloning reference audio."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

from vntts.utils.exceptions import ValidationError

MIN_VOICED_DURATION_SECONDS = 6.0
ENGINE_REFERENCE_LIMIT_SECONDS = 8.0
VOICE_FRAME_SECONDS = 0.02
VOICE_RMS_THRESHOLD = 10.0 ** (-50.0 / 20.0)
CLIPPING_SAMPLE_THRESHOLD = 0.99
CLIPPING_RATIO_THRESHOLD = 0.001
TARGET_PEAK = 10.0 ** (-3.0 / 20.0)


@dataclass(frozen=True)
class PreprocessedReference:
    """Decoded mono reference audio plus measurements for the UI."""

    audio: np.ndarray
    sample_rate: int
    duration_seconds: float
    warnings: tuple[str, ...]


def preprocess_reference_audio(source: Path) -> PreprocessedReference:
    """Decode, validate and peak-normalize a reference without trim or denoise."""

    source_path = source.expanduser().resolve()
    try:
        decoded, sample_rate = sf.read(
            source_path,
            dtype="float32",
            always_2d=True,
        )
    except (OSError, RuntimeError, ValueError, sf.SoundFileError) as exc:
        raise ValidationError(
            "Không thể giải mã file âm thanh mẫu. Hãy chọn file audio hợp lệ."
        ) from exc

    if sample_rate <= 0 or decoded.shape[0] == 0 or decoded.shape[1] == 0:
        raise ValidationError("File âm thanh mẫu không chứa dữ liệu audio hợp lệ.")
    if not bool(np.isfinite(decoded).all()):
        raise ValidationError("File âm thanh mẫu chứa dữ liệu audio không hợp lệ.")

    mono = np.mean(decoded, axis=1, dtype=np.float64).astype(np.float32)
    mono -= np.float32(np.mean(mono, dtype=np.float64))
    duration_seconds = float(mono.size / sample_rate)
    voiced_duration = _estimate_voiced_duration(mono, sample_rate)
    if voiced_duration <= VOICE_FRAME_SECONDS:
        raise ValidationError(
            "Mẫu giọng không chứa phần có tiếng. Vui lòng ghi âm lại rõ ràng hơn."
        )
    if voiced_duration < MIN_VOICED_DURATION_SECONDS:
        raise ValidationError(
            "Phần có tiếng của mẫu giọng phải dài ít nhất 6 giây "
            f"(hiện khoảng {voiced_duration:.1f} giây)."
        )

    warnings: list[str] = []
    if duration_seconds > ENGINE_REFERENCE_LIMIT_SECONDS:
        warnings.append(
            "Mẫu giọng dài hơn 8 giây; VieNeu chỉ sử dụng 8 giây đầu."
        )
    clipping_ratio = float(np.mean(np.abs(mono) > CLIPPING_SAMPLE_THRESHOLD))
    if clipping_ratio > CLIPPING_RATIO_THRESHOLD:
        warnings.append(
            "Mẫu giọng bị clipping; vui lòng ghi âm lại với âm lượng thấp hơn."
        )

    peak = float(np.max(np.abs(mono)))
    if peak > 0.0:
        mono = np.asarray(mono * (TARGET_PEAK / peak), dtype=np.float32)
    return PreprocessedReference(
        audio=np.ascontiguousarray(mono),
        sample_rate=int(sample_rate),
        duration_seconds=duration_seconds,
        warnings=tuple(warnings),
    )


def _estimate_voiced_duration(audio: np.ndarray, sample_rate: int) -> float:
    """Estimate voiced time using short-frame RMS without modifying the waveform."""

    frame_size = max(1, round(sample_rate * VOICE_FRAME_SECONDS))
    frame_count = int(np.ceil(audio.size / frame_size))
    padded = np.pad(audio, (0, frame_count * frame_size - audio.size))
    frames = padded.reshape(frame_count, frame_size).astype(np.float64, copy=False)
    rms = np.sqrt(np.mean(np.square(frames), axis=1))
    voiced_frames = int(np.count_nonzero(rms >= VOICE_RMS_THRESHOLD))
    return min(float(audio.size / sample_rate), voiced_frames * frame_size / sample_rate)
