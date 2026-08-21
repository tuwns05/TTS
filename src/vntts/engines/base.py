"""Engine-neutral TTS contracts and shared adapter helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from threading import Event

import numpy as np

from vntts.db.models import (
    EngineInfo,
    EngineRuntimeInfo,
    EngineSynthesisOptions,
    SynthesisResult,
    VoiceInfo,
)
from vntts.utils.exceptions import SynthesisError


@dataclass(frozen=True)
class EngineCapabilities:
    """Features and devices supported by an engine adapter."""

    voice_cloning: bool
    native_speed_control: bool
    native_pitch_control: bool
    streaming: bool
    cpu_supported: bool
    gpu_supported: bool
    supported_style_ids: tuple[str, ...] = ("tu_nhien",)


class BaseTTSEngine(ABC):
    """Contract implemented by every concrete TTS engine adapter."""

    @property
    @abstractmethod
    def engine_info(self) -> EngineInfo:
        """Return stable metadata without loading the model."""

    @property
    @abstractmethod
    def capabilities(self) -> EngineCapabilities:
        """Return capabilities available through this adapter."""

    def is_available(self) -> bool:
        """Return whether local runtime dependencies and model assets exist.

        Adapters should override this lightweight check when they depend on
        optional SDKs or external model files. The default keeps simple test
        adapters backwards compatible.
        """

        return True

    @property
    def runtime_info(self) -> EngineRuntimeInfo | None:
        """Return the active backend/device after the model has loaded."""

        return None

    def encode_voice_reference(self, reference_audio_path: str) -> tuple[np.ndarray, np.ndarray]:
        """Extract reusable voice features when the adapter supports enrollment."""

        raise SynthesisError("Engine không hỗ trợ trích xuất đặc điểm giọng.")

    @abstractmethod
    def load(self, device: str) -> None:
        """Load engine resources for the requested device."""

    @abstractmethod
    def unload(self) -> None:
        """Release resources held by the engine."""

    @abstractmethod
    def is_loaded(self) -> bool:
        """Return whether engine resources are ready."""

    @abstractmethod
    def list_voices(self) -> list[VoiceInfo]:
        """List voices exposed by the current engine."""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        options: EngineSynthesisOptions,
        cancel_event: Event | None = None,
    ) -> SynthesisResult:
        """Synthesize text into an engine-neutral audio result."""


def to_mono_float32(value: object) -> np.ndarray:
    """Convert an SDK tensor/array into the domain mono float32 format."""

    candidate = value
    detach = getattr(candidate, "detach", None)
    if callable(detach):
        candidate = detach()
        cpu = getattr(candidate, "cpu", None)
        if callable(cpu):
            candidate = cpu()
        numpy_method = getattr(candidate, "numpy", None)
        if callable(numpy_method):
            candidate = numpy_method()

    try:
        audio = np.asarray(candidate, dtype=np.float32)
    except (TypeError, ValueError) as exc:
        raise SynthesisError("Engine trả về dữ liệu âm thanh không hợp lệ.") from exc

    audio = np.squeeze(audio)
    if audio.ndim != 1 or audio.size == 0:
        raise SynthesisError("Engine phải trả về một waveform mono không rỗng.")
    if not bool(np.isfinite(audio).all()):
        raise SynthesisError("Waveform chứa giá trị không hữu hạn.")
    return np.ascontiguousarray(audio, dtype=np.float32)
