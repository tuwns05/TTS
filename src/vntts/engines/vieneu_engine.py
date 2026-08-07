"""Local-only VieNeu-TTS v2-Turbo and v3-Turbo adapters."""

from __future__ import annotations

import importlib
import importlib.util
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from vntts.db.models import (
    VIENEU_V2_ENGINE_ID,
    VIENEU_V3_ENGINE_ID,
    EngineInfo,
    EngineSynthesisOptions,
    SynthesisResult,
    VoiceInfo,
)
from vntts.engines.base import (
    BaseTTSEngine,
    EngineCapabilities,
    to_mono_float32,
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

    def close(self) -> None: ...


VieNeuFactory = Callable[..., _VieNeuRuntime]


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
    except Exception:
        return False


class BaseVieNeuEngine(BaseTTSEngine):
    """Adapt VieNeu preset-voice inference using local paths only."""

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
                VoiceInfo(voice_id=str(voice_id), display_name=str(description))
                for description, voice_id in raw_voices
            ]
        except Exception as exc:
            close = locals().get("runtime")
            close_method = getattr(close, "close", None)
            if callable(close_method):
                close_method()
            raise EngineLoadError(f"Không thể khởi tạo {self._info.display_name}.") from exc

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
        if options.voice_id not in {voice.voice_id for voice in self._voices}:
            raise ValidationError("Giọng đọc không tồn tại trong engine đã chọn.")

        try:
            if options.reference_audio_path is not None:
                if not self._capabilities.voice_cloning:
                    raise ValidationError(
                        f"{self._info.display_name} không hỗ trợ Voice Cloning."
                    )
                reference_path = Path(options.reference_audio_path).expanduser().resolve()
                if not reference_path.is_file():
                    raise ValidationError("Không tìm thấy tệp âm thanh tham chiếu.")
                audio = runtime.infer(text=text.strip(), ref_audio=str(reference_path))
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
            return "cuda" if self._capabilities.gpu_supported and _cuda_available() else "cpu"
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


class VieNeuV3Engine(BaseVieNeuEngine):
    """Run bundled v3 assets without repository IDs or remote mode."""

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
    )

    def __init__(
        self,
        backbone_path: Path,
        codec_path: Path,
        *,
        sample_rate: int = 48_000,
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
