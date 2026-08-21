"""Synthesize speech through an engine-neutral workflow."""

from __future__ import annotations

import time
from concurrent.futures import CancelledError
from inspect import Parameter, signature
from threading import Event

import numpy as np
from loguru import logger

from vntts.db.models import (
    AudioEffects,
    EngineRuntimeInfo,
    EngineSynthesisOptions,
    SynthesisRequest,
    SynthesisResult,
    VoiceInfo,
)
from vntts.engines.base import BaseTTSEngine
from vntts.engines.factory import EngineFactory, EngineLifecycleManager, EngineRegistry
from vntts.utils.exceptions import (
    AppError,
    EngineLoadError,
    SynthesisError,
    ValidationError,
)


def _synthesize_with_cancel_event(
    engine: BaseTTSEngine,
    text: str,
    options: EngineSynthesisOptions,
    cancel_event: Event | None,
) -> SynthesisResult:
    """Call new engines with cancellation while retaining legacy adapters."""

    synthesize = engine.synthesize
    try:
        parameters = signature(synthesize).parameters.values()
        accepts_cancel_event = any(
            parameter.name == "cancel_event"
            or parameter.kind is Parameter.VAR_KEYWORD
            for parameter in parameters
        )
    except (TypeError, ValueError):
        accepts_cancel_event = False
    if accepts_cancel_event:
        return synthesize(text, options, cancel_event=cancel_event)
    return synthesize(text, options)


def _phase_vocoder(spec: np.ndarray, rate: float, hop_length: int) -> np.ndarray:
    """Stretch an STFT along time while preserving its perceived pitch."""

    time_steps = np.arange(0, spec.shape[1], rate, dtype=np.float64)
    output = np.empty((spec.shape[0], len(time_steps)), dtype=np.complex64)
    phase_advance = np.linspace(0, np.pi * hop_length, spec.shape[0])
    phase_accumulator = np.angle(spec[:, 0])
    padded = np.pad(spec, ((0, 0), (0, 2)), mode="constant")

    for output_index, step in enumerate(time_steps):
        frame_index = int(step)
        fraction = step - frame_index
        first = padded[:, frame_index]
        second = padded[:, frame_index + 1]
        magnitude = (1.0 - fraction) * np.abs(first) + fraction * np.abs(second)
        output[:, output_index] = magnitude * np.exp(1j * phase_accumulator)

        phase_delta = np.angle(second) - np.angle(first) - phase_advance
        phase_delta -= 2.0 * np.pi * np.round(phase_delta / (2.0 * np.pi))
        phase_accumulator += phase_advance + phase_delta

    return output


def _time_stretch(audio: np.ndarray, rate: float) -> np.ndarray:
    """Change duration without changing pitch using an STFT phase vocoder."""

    from scipy import signal

    if audio.size < 64:
        target_size = max(1, round(audio.size / rate))
        return signal.resample(audio, target_size).astype(np.float32)

    n_fft = min(2_048, 2 ** int(np.floor(np.log2(audio.size))))
    hop_length = max(1, n_fft // 4)
    _, _, spec = signal.stft(
        audio,
        window="hann",
        nperseg=n_fft,
        noverlap=n_fft - hop_length,
        boundary="zeros",
        padded=True,
    )
    stretched_spec = _phase_vocoder(spec, rate, hop_length)
    _, stretched = signal.istft(
        stretched_spec,
        window="hann",
        nperseg=n_fft,
        noverlap=n_fft - hop_length,
        input_onesided=True,
        boundary=True,
    )
    target_size = max(1, round(audio.size / rate))
    if stretched.size < target_size:
        stretched = np.pad(stretched, (0, target_size - stretched.size))
    return np.asarray(stretched[:target_size], dtype=np.float32)


def _pitch_shift(audio: np.ndarray, semitones: float) -> np.ndarray:
    """Shift pitch by semitones while preserving the original duration."""

    from scipy import signal

    ratio = float(2.0 ** (semitones / 12.0))
    resampled_size = max(1, round(audio.size / ratio))
    resampled = signal.resample(audio, resampled_size).astype(np.float32)
    shifted = _time_stretch(resampled, 1.0 / ratio)
    if shifted.size < audio.size:
        shifted = np.pad(shifted, (0, audio.size - shifted.size))
    return np.asarray(shifted[: audio.size], dtype=np.float32)


def apply_audio_effects(
    result: SynthesisResult,
    effects: AudioEffects,
) -> SynthesisResult:
    """Apply independent speed, pitch and gain controls to a mono waveform."""

    is_neutral = (
        effects.speed == 1.0
        and effects.pitch_semitones == 0.0
        and effects.volume_db == 0.0
    )
    if is_neutral:
        return result

    audio = np.asarray(result.audio, dtype=np.float32)
    try:
        if effects.pitch_semitones != 0.0:
            audio = _pitch_shift(audio, effects.pitch_semitones)
        if effects.speed != 1.0:
            audio = _time_stretch(audio, effects.speed)

        if effects.volume_db != 0.0:
            gain = float(10.0 ** (effects.volume_db / 20.0))
            audio = audio * gain
    except Exception as exc:
        raise SynthesisError("Không thể áp dụng hiệu ứng âm thanh.") from exc

    processed = np.clip(audio, -1.0, 1.0).astype(np.float32, copy=False)
    return SynthesisResult(np.ascontiguousarray(processed), result.sample_rate)


class SynthesizeSpeech:
    """Validate a request, prepare an engine and return synthesized audio."""

    def __init__(
        self,
        factory: EngineFactory,
        registry: EngineRegistry,
        device: str = "auto",
        lifecycle: EngineLifecycleManager | None = None,
    ) -> None:
        self._factory = factory
        self._registry = registry
        self._device = device
        self._lifecycle = lifecycle or EngineLifecycleManager(factory)

    def prepare_engine(
        self,
        engine_id: str,
        device: str | None = None,
        force_reload: bool = False,
    ) -> list[VoiceInfo]:
        """Create and load an engine if needed, then return its voices."""

        if not self._registry.contains(engine_id):
            self._factory.create(engine_id)
        requested_device = device or self._device
        engine = self._lifecycle.get(engine_id)
        if (
            force_reload
            or not engine.is_loaded()
            or self._lifecycle.active_engine_id != engine_id
        ):
            logger.info("Bắt đầu load engine", engine_id=engine_id)
            try:
                engine = self._lifecycle.activate(
                    engine_id,
                    requested_device,
                    force_reload=force_reload,
                )
            except AppError:
                raise
            except Exception as exc:
                logger.exception("Load engine thất bại", engine_id=engine_id)
                raise EngineLoadError(f"Không thể tải engine '{engine_id}'.") from exc
            logger.info("Load engine thành công", engine_id=engine_id)
        self._device = requested_device
        return engine.list_voices()

    def runtime_info(self, engine_id: str) -> EngineRuntimeInfo | None:
        """Return the backend and device currently active for an engine."""

        engine = self._lifecycle.get(engine_id)
        if self._lifecycle.active_engine_id != engine_id or not engine.is_loaded():
            return None
        info = engine.runtime_info
        if info is not None:
            return info
        return EngineRuntimeInfo(
            engine_id=engine.engine_info.engine_id,
            display_name=engine.engine_info.display_name,
            device="cpu",
            backend="native",
            device_name="CPU",
        )

    def execute(
        self,
        request: SynthesisRequest,
        cancel_event: Event | None = None,
    ) -> SynthesisResult:
        """Run synthesis without logging the user's text payload."""

        if cancel_event is not None and cancel_event.is_set():
            raise CancelledError()

        text = request.text.strip()
        if not text:
            raise ValidationError("Văn bản không được để trống.")
        if not self._registry.contains(request.engine_id):
            self._factory.create(request.engine_id)

        voices = self.prepare_engine(request.engine_id)
        capabilities = self._registry.get_capabilities(request.engine_id)
        uses_cloned_voice = (
            request.options.reference_audio_path is not None
            or request.options.voice_artifact_path is not None
        )
        if uses_cloned_voice and not capabilities.voice_cloning:
            raise ValidationError("Engine đã chọn không hỗ trợ nhân bản giọng.")
        if (
            not uses_cloned_voice
            and request.options.voice_id not in {voice.voice_id for voice in voices}
        ):
            raise ValidationError("Giọng đọc không tồn tại trong engine đã chọn.")
        supported_styles = capabilities.supported_style_ids
        if request.options.style_id not in supported_styles:
            raise ValidationError(
                "Phong cách đọc không được engine đã chọn hỗ trợ."
            )

        started_at = time.perf_counter()
        logger.info(
            "Bắt đầu tổng hợp",
            engine_id=request.engine_id,
            text_length=len(text),
        )
        try:
            raw_result = self._lifecycle.run_with_active(
                request.engine_id,
                lambda engine: _synthesize_with_cancel_event(
                    engine,
                    text,
                    request.options,
                    cancel_event,
                ),
            )
            if cancel_event is not None and cancel_event.is_set():
                raise CancelledError()
            result = apply_audio_effects(raw_result, request.effects)
        except CancelledError:
            raise
        except AppError:
            raise
        except Exception as exc:
            logger.exception("Tổng hợp thất bại", engine_id=request.engine_id)
            raise SynthesisError("Không thể tổng hợp giọng nói.") from exc
        logger.info(
            "Tổng hợp hoàn tất",
            engine_id=request.engine_id,
            duration_seconds=round(time.perf_counter() - started_at, 3),
        )
        return result

    def encode_voice_reference(
        self,
        engine_id: str,
        reference_audio_path: str,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Extract reusable clone features with the active engine."""

        self.prepare_engine(engine_id)
        capabilities = self._registry.get_capabilities(engine_id)
        if not capabilities.voice_cloning:
            raise ValidationError("Engine đã chọn không hỗ trợ nhân bản giọng.")
        return self._lifecycle.run_with_active(
            engine_id,
            lambda engine: engine.encode_voice_reference(reference_audio_path),
        )

    def unload_all(self) -> None:
        """Release every cached engine adapter during shutdown."""

        self._lifecycle.unload_all()
