"""Deterministic test doubles for engine-independent tests."""

from __future__ import annotations

import time

import numpy as np

from vntts.db.models import EngineInfo, EngineSynthesisOptions, SynthesisResult, VoiceInfo
from vntts.engines.base import BaseTTSEngine, EngineCapabilities
from vntts.utils.exceptions import EngineLoadError, EngineNotLoadedError, ValidationError


class StubTTSEngine(BaseTTSEngine):
    """Provide predictable audio without requiring a real model in unit tests."""

    INFO = EngineInfo("stub", "Stub TTS Engine", version="1")
    CAPABILITIES = EngineCapabilities(
        voice_cloning=False,
        native_speed_control=False,
        native_pitch_control=False,
        streaming=False,
        cpu_supported=True,
        gpu_supported=False,
    )
    VOICES = (
        VoiceInfo("female-south", "Nữ miền Nam"),
        VoiceInfo("female-north", "Nữ miền Bắc"),
        VoiceInfo("male-south", "Nam miền Nam"),
    )

    def __init__(self, sample_rate: int = 24_000, processing_delay: float = 0) -> None:
        self._sample_rate = sample_rate
        self._processing_delay = max(0.0, processing_delay)
        self._loaded = False

    @property
    def engine_info(self) -> EngineInfo:
        return self.INFO

    @property
    def capabilities(self) -> EngineCapabilities:
        return self.CAPABILITIES

    def load(self, device: str) -> None:
        if device not in {"auto", "cpu"}:
            raise EngineLoadError("Test stub chỉ hỗ trợ CPU hoặc auto.")
        self._loaded = True

    def unload(self) -> None:
        self._loaded = False

    def is_loaded(self) -> bool:
        return self._loaded

    def list_voices(self) -> list[VoiceInfo]:
        return list(self.VOICES)

    def synthesize(
        self,
        text: str,
        options: EngineSynthesisOptions,
    ) -> SynthesisResult:
        if not self._loaded:
            raise EngineNotLoadedError("Test stub chưa được load.")
        if not text.strip():
            raise ValidationError("Văn bản không được để trống.")
        voice_ids = {voice.voice_id for voice in self.VOICES}
        if options.voice_id not in voice_ids:
            raise ValidationError("Giọng đọc không tồn tại trong test stub.")

        time.sleep(self._processing_delay)
        sample_count = max(1, int(self._sample_rate * 0.25))
        timeline = np.arange(sample_count, dtype=np.float32) / self._sample_rate
        audio = (0.15 * np.sin(2 * np.pi * 180 * timeline)).astype(np.float32)
        return SynthesisResult(audio, self._sample_rate)
