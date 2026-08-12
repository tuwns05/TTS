"""VieNeu-TTS v2 and v3 Turbo adapters."""

from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import re
import warnings
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import numpy as np
from loguru import logger

from vntts.db.models import (
    VIENEU_V2_ENGINE_ID,
    VIENEU_V3_ENGINE_ID,
    EngineInfo,
    EngineRuntimeInfo,
    EngineSynthesisOptions,
    SynthesisResult,
    VoiceInfo,
)
from vntts.engines.base import (
    BaseTTSEngine,
    EngineCapabilities,
    to_mono_float32,
)
from vntts.engines.model_bundle import (
    configure_offline_huggingface_cache,
    validate_vieneu_v3_bundle,
)
from vntts.utils.exceptions import (
    EngineLoadError,
    EngineNotLoadedError,
    SynthesisError,
    ValidationError,
)


class _VieNeuRuntime(Protocol):
    def list_preset_voices(self) -> list[tuple[str, str]]: ...

    def get_preset_voice(self, voice_name: str) -> object: ...

    def infer(self, **kwargs: object) -> object: ...

    def encode_reference(self, ref_audio: str, denoise: bool = True) -> object: ...

    def close(self) -> None: ...


VieNeuFactory = Callable[..., _VieNeuRuntime]
VIENEU_V3_REPOSITORY = "pnnbao-ump/VieNeu-TTS-v3-Turbo"
VIENEU_V3_TOKENIZER_REPOSITORY = "OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano"


def _voice_display_name(description: object, voice_id: object) -> str:
    """Remove preset style metadata now presented by its own UI control."""

    display_name = str(description).strip() or str(voice_id)
    return re.sub(
        r"\s*·\s*Phong cách\s+.+$",
        "",
        display_name,
        flags=re.IGNORECASE,
    ).strip()


def _default_vieneu_factory(**kwargs: object) -> _VieNeuRuntime:
    module = importlib.import_module("vieneu")
    factory = getattr(module, "Vieneu", None)
    if not callable(factory):
        raise EngineLoadError("Gói vieneu không cung cấp Vieneu factory.")
    return factory(**kwargs)


def _sdk_is_installed() -> bool:
    try:
        return importlib.util.find_spec("vieneu") is not None
    except (ImportError, ValueError):
        return False


def _cuda_available() -> bool:
    try:
        torch = importlib.import_module("torch")
        return bool(torch.cuda.is_available())
    except Exception:  # noqa: BLE001 - CUDA probing must safely degrade to CPU
        return False


class BaseVieNeuEngine(BaseTTSEngine):
    """Adapt the legacy VieNeu v2 standard mode using local paths only."""

    def __init__(
        self,
        *,
        engine_info: EngineInfo,
        capabilities: EngineCapabilities,
        backbone_path: Path,
        codec_path: Path,
        sample_rate: int = 24_000,
        sdk_factory: VieNeuFactory | None = None,
    ) -> None:
        self._info = engine_info
        self._capabilities = capabilities
        self._backbone_path = backbone_path.resolve()
        self._codec_path = codec_path.resolve()
        self._sample_rate = sample_rate
        self._sdk_factory = sdk_factory or _default_vieneu_factory
        self._injected_factory = sdk_factory is not None
        self._runtime: _VieNeuRuntime | None = None
        self._voices: list[VoiceInfo] = []

    @property
    def engine_info(self) -> EngineInfo:
        return self._info

    @property
    def capabilities(self) -> EngineCapabilities:
        return self._capabilities

    def is_available(self) -> bool:
        sdk_exists = self._injected_factory or _sdk_is_installed()
        return sdk_exists and self._backbone_path.exists() and self._codec_path.exists()

    def load(self, device: str) -> None:
        if self._runtime is not None:
            return
        missing = [
            str(path)
            for path in (self._backbone_path, self._codec_path)
            if not path.exists()
        ]
        if missing:
            raise EngineLoadError("Thiếu model VieNeu local: " + ", ".join(missing))

        resolved_device = self._resolve_device(device)
        try:
            runtime = self._sdk_factory(
                mode="standard",
                backbone_repo=str(self._backbone_path),
                backbone_device=resolved_device,
                codec_repo=str(self._codec_path),
                codec_device=resolved_device,
            )
            raw_voices = runtime.list_preset_voices()
            voices = [
                VoiceInfo(
                    voice_id=str(voice_id),
                    display_name=_voice_display_name(description, voice_id),
                )
                for description, voice_id in raw_voices
            ]
        except Exception as exc:
            close = locals().get("runtime")
            close_method = getattr(close, "close", None)
            if callable(close_method):
                close_method()
            raise EngineLoadError(
                f"Không thể khởi tạo {self._info.display_name}."
            ) from exc

        if not voices:
            runtime.close()
            raise EngineLoadError("VieNeu không cung cấp giọng dựng sẵn nào.")
        self._runtime = runtime
        self._voices = voices

    def unload(self) -> None:
        runtime, self._runtime = self._runtime, None
        self._voices = []
        if runtime is not None:
            try:
                runtime.close()
            except Exception as exc:
                raise EngineLoadError(
                    f"Không thể giải phóng {self._info.display_name}."
                ) from exc

    def is_loaded(self) -> bool:
        return self._runtime is not None

    def list_voices(self) -> list[VoiceInfo]:
        if self._runtime is None:
            raise EngineNotLoadedError(f"{self._info.display_name} chưa được load.")
        return list(self._voices)

    def synthesize(
        self,
        text: str,
        options: EngineSynthesisOptions,
    ) -> SynthesisResult:
        runtime = self._runtime
        if runtime is None:
            raise EngineNotLoadedError(f"{self._info.display_name} chưa được load.")
        if not text.strip():
            raise ValidationError("Văn bản không được để trống.")
        if options.reference_audio_path is None and options.voice_id not in {
            voice.voice_id for voice in self._voices
        }:
            raise ValidationError("Giọng đọc không tồn tại trong engine đã chọn.")

        try:
            if options.reference_audio_path is not None:
                if not self._capabilities.voice_cloning:
                    raise ValidationError(
                        f"{self._info.display_name} không hỗ trợ Voice Cloning."
                    )
                reference_path = (
                    Path(options.reference_audio_path).expanduser().resolve()
                )
                if not reference_path.is_file():
                    raise ValidationError("Không tìm thấy tệp âm thanh tham chiếu.")
                audio = runtime.infer(
                    text=text.strip(),
                    ref_audio=str(reference_path),
                )
            else:
                voice = runtime.get_preset_voice(options.voice_id)
                audio = runtime.infer(text=text.strip(), voice=voice)
        except ValidationError:
            raise
        except Exception as exc:
            raise SynthesisError(
                f"{self._info.display_name} không thể tổng hợp giọng nói."
            ) from exc
        return SynthesisResult(to_mono_float32(audio), self._sample_rate)

    def _resolve_device(self, requested: str) -> str:
        if requested not in {"auto", "cpu", "cuda"}:
            raise EngineLoadError(f"Thiết bị '{requested}' không được hỗ trợ.")
        if requested == "auto":
            return (
                "cuda"
                if self._capabilities.gpu_supported and _cuda_available()
                else "cpu"
            )
        if requested == "cuda" and not self._capabilities.gpu_supported:
            raise EngineLoadError(f"{self._info.display_name} không hỗ trợ CUDA.")
        if requested == "cpu" and not self._capabilities.cpu_supported:
            raise EngineLoadError(f"{self._info.display_name} không hỗ trợ CPU.")
        return requested


class VieNeuV2Engine(BaseVieNeuEngine):
    """Run an optional, already-installed v2 model through VieNeu standard mode."""

    INFO = EngineInfo(
        VIENEU_V2_ENGINE_ID,
        "VieNeu-TTS v2-Turbo",
        version="2",
        description="Engine tùy chọn cho máy tầm trung.",
    )
    CAPABILITIES = EngineCapabilities(
        voice_cloning=False,
        native_speed_control=False,
        native_pitch_control=False,
        streaming=False,
        cpu_supported=True,
        gpu_supported=False,
    )

    def __init__(
        self,
        backbone_path: Path,
        codec_path: Path,
        *,
        sample_rate: int = 24_000,
        sdk_factory: VieNeuFactory | None = None,
    ) -> None:
        super().__init__(
            engine_info=self.INFO,
            capabilities=self.CAPABILITIES,
            backbone_path=backbone_path,
            codec_path=codec_path,
            sample_rate=sample_rate,
            sdk_factory=sdk_factory,
        )


class VieNeuV3Engine(BaseTTSEngine):
    """Run VieNeu v3 Turbo from the development cache or bundled assets."""

    INFO = EngineInfo(
        VIENEU_V3_ENGINE_ID,
        "VieNeu-TTS v3-Turbo",
        version="3",
        description="Engine chất lượng cao, dùng model local đi kèm bản production.",
    )
    CAPABILITIES = EngineCapabilities(
        voice_cloning=True,
        native_speed_control=False,
        native_pitch_control=False,
        streaming=False,
        cpu_supported=True,
        gpu_supported=True,
        supported_style_ids=("tu_nhien", "tin_tuc", "doc_truyen"),
    )

    def __init__(
        self,
        model_path: Path | None = None,
        *,
        tokenizer_path: Path | None = None,
        bundle_path: Path | None = None,
        allow_download: bool = False,
        backend: str = "auto",
        sample_rate: int = 48_000,
        sdk_factory: VieNeuFactory | None = None,
    ) -> None:
        self._model_path = model_path.resolve() if model_path is not None else None
        self._tokenizer_path = (
            tokenizer_path.resolve() if tokenizer_path is not None else None
        )
        self._allow_download = allow_download
        self._bundle_path = bundle_path.resolve() if bundle_path is not None else None
        self._backend = backend
        self._sample_rate = sample_rate
        self._sdk_factory = sdk_factory or _default_vieneu_factory
        self._injected_factory = sdk_factory is not None
        self._runtime: _VieNeuRuntime | None = None
        self._voices: list[VoiceInfo] = []
        self._runtime_info: EngineRuntimeInfo | None = None

    @property
    def engine_info(self) -> EngineInfo:
        return self.INFO

    @property
    def capabilities(self) -> EngineCapabilities:
        return self.CAPABILITIES

    @property
    def runtime_info(self) -> EngineRuntimeInfo | None:
        return self._runtime_info

    def is_available(self) -> bool:
        sdk_exists = self._injected_factory or _sdk_is_installed()
        if self._bundle_path is not None:
            return (
                sdk_exists
                and (self._bundle_path / "manifest.json").is_file()
                and (self._bundle_path / "hub").is_dir()
            )
        model_available = self._allow_download or (
            self._model_path is not None and self._model_path.is_dir()
        )
        tokenizer_available = self._allow_download or (
            self._tokenizer_path is not None and self._tokenizer_path.is_dir()
        )
        return sdk_exists and model_available and tokenizer_available

    def load(self, device: str) -> None:
        if self._runtime is not None:
            return
        bundle_info = None
        if self._bundle_path is not None:
            bundle_info = validate_vieneu_v3_bundle(
                self._bundle_path,
                verify_hashes=True,
            )
            configure_offline_huggingface_cache(bundle_info.hub_cache)
            if not self._injected_factory:
                try:
                    installed_sdk = importlib.metadata.version("vieneu")
                except importlib.metadata.PackageNotFoundError as exc:
                    raise EngineLoadError("Thiếu SDK vieneu trong bản đóng gói.") from exc
                if installed_sdk != bundle_info.sdk_version:
                    raise EngineLoadError(
                        "SDK vieneu không khớp manifest model "
                        f"({installed_sdk} != {bundle_info.sdk_version})."
                    )
        elif not self._allow_download:
            missing = []
            if self._model_path is None or not self._model_path.is_dir():
                missing.append("model")
            if self._tokenizer_path is None or not self._tokenizer_path.is_dir():
                missing.append("MOSS tokenizer")
            if missing:
                raise EngineLoadError(
                    "Thiếu tài nguyên VieNeu v3 bundled: " + ", ".join(missing)
                )

        resolved_device = self._resolve_device(device)
        if bundle_info is not None:
            model_source = VIENEU_V3_REPOSITORY
            tokenizer_source = VIENEU_V3_TOKENIZER_REPOSITORY
        else:
            model_source = (
                str(self._model_path)
                if self._model_path is not None and self._model_path.is_dir()
                else VIENEU_V3_REPOSITORY
            )
            tokenizer_source = (
                str(self._tokenizer_path)
                if self._tokenizer_path is not None and self._tokenizer_path.is_dir()
                else VIENEU_V3_TOKENIZER_REPOSITORY
            )
        selected_backend = self._backend_for_device(resolved_device)
        attempts = [(resolved_device, selected_backend)]
        if device == "auto" and resolved_device == "cuda":
            attempts.append(("cpu", "onnx"))

        gpu_failure: Exception | None = None
        for attempt_device, attempt_backend in attempts:
            runtime = None
            try:
                runtime = self._sdk_factory(
                    mode="v3turbo",
                    backbone_repo=model_source,
                    moss_tokenizer=tokenizer_source,
                    device=attempt_device,
                    backend=attempt_backend,
                )
                raw_voices = runtime.list_preset_voices()
                voices = [
                    VoiceInfo(
                        voice_id=str(voice_id),
                        display_name=_voice_display_name(description, voice_id),
                    )
                    for description, voice_id in raw_voices
                ]
                if not voices:
                    raise EngineLoadError(
                        "VieNeu v3 không cung cấp giọng dựng sẵn nào."
                    )
                fallback_reason = None
                if gpu_failure is not None:
                    fallback_reason = (
                        "Không thể khởi tạo GPU; đã tự chuyển sang CPU."
                    )
                self._runtime = runtime
                self._voices = voices
                self._runtime_info = EngineRuntimeInfo(
                    engine_id=self.INFO.engine_id,
                    display_name=self.INFO.display_name,
                    device=attempt_device,
                    backend=attempt_backend,
                    device_name=self._device_name(attempt_device),
                    fallback_reason=fallback_reason,
                )
                return
            except Exception as exc:
                close_method = getattr(runtime, "close", None)
                if callable(close_method):
                    close_method()
                if attempt_device == "cuda" and len(attempts) > 1:
                    gpu_failure = exc
                    logger.opt(exception=exc).warning(
                        "Không thể load VieNeu v3 trên GPU; fallback CPU"
                    )
                    self._release_cuda_cache()
                    continue
                raise EngineLoadError(
                    "Không thể khởi tạo VieNeu-TTS v3-Turbo "
                    f"trên {attempt_device.upper()}."
                ) from exc

    def unload(self) -> None:
        runtime, self._runtime = self._runtime, None
        self._voices = []
        previous_device = self._runtime_info.device if self._runtime_info else None
        self._runtime_info = None
        if runtime is not None:
            try:
                runtime.close()
            except Exception as exc:
                raise EngineLoadError(
                    "Không thể giải phóng VieNeu-TTS v3-Turbo."
                ) from exc
        if previous_device == "cuda":
            self._release_cuda_cache()

    def is_loaded(self) -> bool:
        return self._runtime is not None

    def list_voices(self) -> list[VoiceInfo]:
        if self._runtime is None:
            raise EngineNotLoadedError("VieNeu-TTS v3-Turbo chưa được load.")
        return list(self._voices)

    def synthesize(
        self,
        text: str,
        options: EngineSynthesisOptions,
    ) -> SynthesisResult:
        runtime = self._runtime
        if runtime is None:
            raise EngineNotLoadedError("VieNeu-TTS v3-Turbo chưa được load.")
        if not text.strip():
            raise ValidationError("Văn bản không được để trống.")
        if (
            options.reference_audio_path is None
            and options.voice_artifact_path is None
            and options.voice_id not in {voice.voice_id for voice in self._voices}
        ):
            raise ValidationError("Giọng đọc không tồn tại trong engine đã chọn.")

        try:
            if options.voice_artifact_path is not None:
                artifact_path = Path(options.voice_artifact_path).expanduser().resolve()
                if not artifact_path.is_file():
                    raise ValidationError("Không tìm thấy đặc điểm giọng đã lưu.")
                try:
                    with np.load(artifact_path, allow_pickle=False) as artifact:
                        speaker_emb = np.asarray(
                            artifact["speaker_emb"], dtype=np.float32
                        )
                        ref_codes = np.asarray(artifact["ref_codes"], dtype=np.int64)
                except (OSError, ValueError, KeyError) as exc:
                    raise ValidationError(
                        "Dữ liệu đặc điểm giọng không hợp lệ."
                    ) from exc
                audio = runtime.infer(
                    text=text.strip(),
                    voice={"speaker_emb": speaker_emb, "codes": ref_codes},
                    style=options.style_id,
                )
            elif options.reference_audio_path is not None:
                reference_path = (
                    Path(options.reference_audio_path).expanduser().resolve()
                )
                if not reference_path.is_file():
                    raise ValidationError("Không tìm thấy tệp âm thanh tham chiếu.")
                with warnings.catch_warnings():
                    warnings.filterwarnings(
                        "ignore",
                        message=(
                            r"In 2\.9, this function's implementation will be changed "
                            r"to use torchaudio\.load_with_torchcodec.*"
                        ),
                        category=UserWarning,
                    )
                    audio = runtime.infer(
                        text=text.strip(),
                        ref_audio=str(reference_path),
                        style=options.style_id,
                    )
            else:
                voice = runtime.get_preset_voice(options.voice_id)
                audio = runtime.infer(
                    text=text.strip(),
                    voice=voice,
                    style=options.style_id,
                )
        except ValidationError:
            raise
        except Exception as exc:
            logger.opt(exception=exc).error(
                "VieNeu-TTS v3-Turbo synthesis failed"
            )
            raise SynthesisError(
                "VieNeu-TTS v3-Turbo không thể tổng hợp giọng nói."
            ) from exc
        return SynthesisResult(to_mono_float32(audio), self._sample_rate)

    def encode_voice_reference(
        self, reference_audio_path: str
    ) -> tuple[np.ndarray, np.ndarray]:
        """Run VieNeu enrollment once and return serializable voice features."""

        runtime = self._runtime
        if runtime is None:
            raise EngineNotLoadedError("VieNeu-TTS v3-Turbo chưa được load.")
        reference_path = Path(reference_audio_path).expanduser().resolve()
        if not reference_path.is_file():
            raise ValidationError("Không tìm thấy tệp âm thanh tham chiếu.")
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=(
                        r"In 2\.9, this function's implementation will be changed "
                        r"to use torchaudio\.load_with_torchcodec.*"
                    ),
                    category=UserWarning,
                )
                speaker_emb, ref_codes = runtime.encode_reference(
                    str(reference_path), denoise=True
                )
            speaker = np.asarray(speaker_emb, dtype=np.float32).reshape(-1)
            codes = np.asarray(ref_codes, dtype=np.int64)
            if speaker.size == 0 or codes.size == 0:
                raise ValueError("empty voice features")
            return np.ascontiguousarray(speaker), np.ascontiguousarray(codes)
        except ValidationError:
            raise
        except Exception as exc:
            raise SynthesisError(
                "Không thể trích xuất đặc điểm giọng bằng VieNeu v3."
            ) from exc

    def _resolve_device(self, requested: str) -> str:
        if requested not in {"auto", "cpu", "cuda"}:
            raise EngineLoadError(f"Thiết bị '{requested}' không được hỗ trợ.")
        if requested == "auto":
            return "cuda" if _cuda_available() else "cpu"
        if requested == "cuda" and not _cuda_available():
            raise EngineLoadError(
                "Không tìm thấy GPU NVIDIA/CUDA khả dụng. Hãy chọn CPU."
            )
        return requested

    def _backend_for_device(self, device: str) -> str:
        if self._backend == "auto":
            return "pytorch" if device == "cuda" else "onnx"
        return self._backend

    @staticmethod
    def _device_name(device: str) -> str:
        if device != "cuda":
            return "CPU"
        try:
            torch = importlib.import_module("torch")
            return str(torch.cuda.get_device_name(torch.cuda.current_device()))
        except Exception:  # noqa: BLE001 - device labeling must not fail a loaded engine
            return "NVIDIA CUDA"

    @staticmethod
    def _release_cuda_cache() -> None:
        try:
            torch = importlib.import_module("torch")
            if bool(torch.cuda.is_available()):
                torch.cuda.empty_cache()
        except Exception:  # noqa: BLE001 - cache cleanup is best-effort during unload
            return
