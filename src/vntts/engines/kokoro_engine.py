"""Local-only adapter for iamdinhthuan/Kokoro-Vietnamese."""

from __future__ import annotations

import gc
import importlib
import importlib.util
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from vntts.db.models import (
    KOKORO_VI_ENGINE_ID,
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


class _KokoroRuntime(Protocol):
    def synthesize(self, text: str) -> tuple[object, str]: ...


KokoroFactory = Callable[..., _KokoroRuntime]


def _default_kokoro_factory(**kwargs: object) -> _KokoroRuntime:
    module = importlib.import_module("kokoro_vietnamese")
    factory = getattr(module, "KokoroVietnamese", None)
    if not callable(factory):
        raise EngineLoadError(
            "Gói kokoro_vietnamese không cung cấp KokoroVietnamese."
        )
    return factory(**kwargs)


def _sdk_is_installed() -> bool:
    try:
        return importlib.util.find_spec("kokoro_vietnamese") is not None
    except (ImportError, ValueError):
        return False


class KokoroVIEngine(BaseTTSEngine):
    """Use only installed PyTorch checkpoints, config and voicepack files."""

    INFO = EngineInfo(
        KOKORO_VI_ENGINE_ID,
        "Kokoro-Vietnamese",
        description="Engine CPU tùy chọn sử dụng voicepack dựng sẵn.",
    )
    CAPABILITIES = EngineCapabilities(
        voice_cloning=False,
        native_speed_control=False,
        native_pitch_control=False,
        streaming=False,
        cpu_supported=True,
        gpu_supported=False,
    )
    VOICE_NAMES = {
        "diem_trinh": "Diễm Trinh",
        "hung_thinh": "Hưng Thịnh",
        "mai_linh": "Mai Linh",
        "mai_loan": "Mai Loan",
        "manh_dung": "Mạnh Dũng",
        "my_yen": "Mỹ Yến",
        "ngoc_huyen": "Ngọc Huyền",
        "phat_tai": "Phát Tài",
        "thanh_dat": "Thanh Đạt",
        "thuc_trinh": "Thục Trinh",
        "tuan_ngoc": "Tuấn Ngọc",
        "storyvert": "storyvert",
        "duc_an": "Đức An",
        "duc_duy": "Đức Duy",
    }

    def __init__(
        self,
        model_path: Path,
        config_path: Path,
        voicepacks_dir: Path,
        *,
        sample_rate: int = 24_000,
        sdk_factory: KokoroFactory | None = None,
    ) -> None:
        self._model_path = model_path.resolve()
        self._config_path = config_path.resolve()
        self._voicepacks_dir = voicepacks_dir.resolve()
        self._sample_rate = sample_rate
        self._sdk_factory = sdk_factory or _default_kokoro_factory
        self._injected_factory = sdk_factory is not None
        self._runtime: _KokoroRuntime | None = None
        self._active_voice_id: str | None = None
        self._voices: list[VoiceInfo] = []

    @property
    def engine_info(self) -> EngineInfo:
        return self.INFO

    @property
    def capabilities(self) -> EngineCapabilities:
        return self.CAPABILITIES

    def is_available(self) -> bool:
        sdk_exists = self._injected_factory or _sdk_is_installed()
        return (
            sdk_exists
            and self._model_path.is_file()
            and self._config_path.is_file()
            and bool(self._discover_voices())
        )

    def load(self, device: str) -> None:
        if self._runtime is not None:
            return
        if device not in {"auto", "cpu"}:
            raise EngineLoadError("Kokoro-Vietnamese adapter chỉ hỗ trợ CPU.")
        if not self._model_path.is_file() or not self._config_path.is_file():
            raise EngineLoadError(
                "Thiếu kokoro_vi.pth hoặc config.json trong model local."
            )
        self._voices = self._discover_voices()
        if not self._voices:
            raise EngineLoadError("Không tìm thấy voicepack Kokoro local hợp lệ.")
        default_voice = next(
            (voice.voice_id for voice in self._voices if voice.voice_id == "diem_trinh"),
            self._voices[0].voice_id,
        )
        self._load_voice(default_voice)

    def unload(self) -> None:
        runtime, self._runtime = self._runtime, None
        self._active_voice_id = None
        self._voices = []
        close = getattr(runtime, "close", None)
        if callable(close):
            try:
                close()
            except Exception as exc:
                raise EngineLoadError("Không thể giải phóng Kokoro-Vietnamese.") from exc
        gc.collect()

    def is_loaded(self) -> bool:
        return self._runtime is not None

    def list_voices(self) -> list[VoiceInfo]:
        if self._runtime is None:
            raise EngineNotLoadedError("Kokoro-Vietnamese chưa được load.")
        return list(self._voices)

    def synthesize(
        self,
        text: str,
        options: EngineSynthesisOptions,
    ) -> SynthesisResult:
        if self._runtime is None:
            raise EngineNotLoadedError("Kokoro-Vietnamese chưa được load.")
        if not text.strip():
            raise ValidationError("Văn bản không được để trống.")
        if options.reference_audio_path is not None:
            raise ValidationError("Kokoro-Vietnamese không hỗ trợ Voice Cloning.")
        if options.voice_id not in {voice.voice_id for voice in self._voices}:
            raise ValidationError("Voicepack không tồn tại trong Kokoro-Vietnamese.")
        if self._active_voice_id != options.voice_id:
            self._load_voice(options.voice_id)

        try:
            output = self._runtime.synthesize(text.strip())
            audio = output[0] if isinstance(output, tuple) else output
        except Exception as exc:
            raise SynthesisError("Kokoro-Vietnamese không thể tổng hợp giọng nói.") from exc
        return SynthesisResult(to_mono_float32(audio), self._sample_rate)

    def _discover_voices(self) -> list[VoiceInfo]:
        return [
            VoiceInfo(voice_id, display_name)
            for voice_id, display_name in self.VOICE_NAMES.items()
            if (self._voicepacks_dir / f"{voice_id}.pt").is_file()
        ]

    def _load_voice(self, voice_id: str) -> None:
        voicepack_path = self._voicepacks_dir / f"{voice_id}.pt"
        if not voicepack_path.is_file():
            raise EngineLoadError(f"Thiếu voicepack local '{voice_id}'.")
        old_runtime, self._runtime = self._runtime, None
        close = getattr(old_runtime, "close", None)
        if callable(close):
            close()
        try:
            self._runtime = self._sdk_factory(
                device="cpu",
                voice=voice_id,
                model_path=str(self._model_path),
                voicepack_path=str(voicepack_path),
                config_path=str(self._config_path),
            )
        except Exception as exc:
            self._active_voice_id = None
            raise EngineLoadError(
                f"Không thể load voicepack Kokoro '{voice_id}'."
            ) from exc
        self._active_voice_id = voice_id
