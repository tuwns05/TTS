"""Offline fake engine used only by development and tests."""

from __future__ import annotations

import time

import numpy as np

from vntts.db.models import (
    FAKE_ENGINE_ID,
    EngineInfo,
    EngineSynthesisOptions,
    SynthesisResult,
    VoiceInfo,
)
from vntts.engines.base import BaseTTSEngine, EngineCapabilities
from vntts.utils.exceptions import EngineLoadError, EngineNotLoadedError, ValidationError


class FakeTTSEngine(BaseTTSEngine):
    """Generate a short sine wave without a TTS SDK or network access."""

    INFO = EngineInfo(
        engine_id=FAKE_ENGINE_ID,
        display_name="Fake TTS Engine",
        version="1.0",
        description="Engine giả phục vụ development và testing.",
    )
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

    def __init__(self, sample_rate: int = 24_000, processing_delay: float = 0.1) -> None:
        self._sample_rate = sample_rate
        self._processing_delay = max(0.0, processing_delay)
        self._loaded = False

    @property
    def engine_info(self) -> EngineInfo:
        """Return fake engine metadata."""

        return self.INFO

    @property
    def capabilities(self) -> EngineCapabilities:
        """Return deliberately limited fake capabilities."""

        return self.CAPABILITIES

    def is_available(self) -> bool:
        """The fake engine has no optional runtime or model files."""

        return True

    def load(self, device: str) -> None:
        """Simulate loading on CPU or automatic device selection."""

        if device not in {"auto", "cpu"}:
            raise EngineLoadError("Fake engine chỉ hỗ trợ thiết bị CPU hoặc auto.")
        time.sleep(min(self._processing_delay, 0.05))
        self._loaded = True

    def unload(self) -> None:
        """Reset the simulated loaded state."""

        self._loaded = False

    def is_loaded(self) -> bool:
        """Return the simulated loaded state."""

        return self._loaded

    def list_voices(self) -> list[VoiceInfo]:
        """Return stable fake voices without loading a model."""

        return list(self.VOICES)

    def synthesize(
        self,
        text: str,
        options: EngineSynthesisOptions,
    ) -> SynthesisResult:
        """Generate deterministic mono float32 audio for UI workflow tests."""

        if not self._loaded:
            raise EngineNotLoadedError("Fake engine chưa được load.")
        if not text.strip():
            raise ValidationError("Văn bản không được để trống.")
        voice_ids = {voice.voice_id for voice in self.VOICES}
        if options.voice_id not in voice_ids:
            raise ValidationError("Giọng đọc không tồn tại trong fake engine.")

        time.sleep(self._processing_delay)
        duration = min(3.0, max(0.25, len(text) * 0.015))
        sample_count = max(1, int(self._sample_rate * duration))
        timeline = np.arange(sample_count, dtype=np.float32) / self._sample_rate
        frequency = 180.0 + 30.0 * sorted(voice_ids).index(options.voice_id)
        audio = (0.15 * np.sin(2.0 * np.pi * frequency * timeline)).astype(np.float32)
        return SynthesisResult(audio=audio, sample_rate=self._sample_rate)
