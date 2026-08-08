"""Engine-neutral TTS contracts and shared adapter helpers."""

from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

from vntts.db.models import (
    AudioEffects,
    EngineInfo,
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
        effects: AudioEffects | None = None,
    ) -> SynthesisResult:
        """Synthesize text into an engine-neutral audio result."""


def build_runtime_call_kwargs(
    *,
    runtime: object,
    method_name: str,
    text: str,
    voice: object | None = None,
    reference_audio_path: str | None = None,
    effects: AudioEffects | None = None,
) -> dict[str, object]:
    """Prepare runtime kwargs while respecting the runtime's supported signature."""

    method = getattr(runtime, method_name, None)
    if not callable(method):
        raise SynthesisError(f"Runtime không hỗ trợ phương thức '{method_name}'.")

    signature = inspect.signature(method)
    parameters = signature.parameters.values()
    accepts_var_kw = any(param.kind == inspect.Parameter.VAR_KEYWORD for param in parameters)
    accepted_names = {
        param.name
        for param in parameters
        if param.kind
        in {
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        }
    }

    kwargs: dict[str, object] = {"text": text}
    if voice is not None:
        kwargs["voice"] = voice
    if reference_audio_path is not None:
        kwargs["ref_audio"] = reference_audio_path
    if effects is not None:
        kwargs["speed"] = effects.speed
        kwargs["pitch"] = effects.pitch_semitones
        kwargs["volume"] = effects.volume_db
        kwargs["pitch_semitones"] = effects.pitch_semitones
        kwargs["volume_db"] = effects.volume_db

    if accepts_var_kw:
        return kwargs

    return {key: value for key, value in kwargs.items() if key in accepted_names}


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
