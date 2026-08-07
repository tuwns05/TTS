"""Pure data models used by TTS and hardware workflows."""

from dataclasses import dataclass

import numpy as np

from vntts.utils.exceptions import ValidationError


VIENEU_V3_ENGINE_ID = "vieneu-v3"
VIENEU_V2_ENGINE_ID = "vieneu-v2"
KOKORO_VI_ENGINE_ID = "kokoro-vi"
FAKE_ENGINE_ID = "fake"


@dataclass(frozen=True)
class EngineInfo:
    """Stable metadata describing an engine without loading its model."""

    engine_id: str
    display_name: str
    version: str | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        if not self.engine_id.strip():
            raise ValidationError("Mã engine không được để trống.")
        if not self.display_name.strip():
            raise ValidationError("Tên hiển thị engine không được để trống.")


@dataclass(frozen=True)
class VoiceInfo:
    """A voice exposed through the engine-neutral contract."""

    voice_id: str
    display_name: str
    is_cloned: bool = False

    def __post_init__(self) -> None:
        if not self.voice_id.strip():
            raise ValidationError("Mã giọng không được để trống.")
        if not self.display_name.strip():
            raise ValidationError("Tên hiển thị giọng không được để trống.")


@dataclass(frozen=True)
class EngineSynthesisOptions:
    """Options interpreted directly by a TTS engine."""

    voice_id: str
    reference_audio_path: str | None = None

    def __post_init__(self) -> None:
        if not self.voice_id.strip():
            raise ValidationError("Vui lòng chọn giọng đọc.")


@dataclass(frozen=True)
class AudioEffects:
    """Post-processing controls collected independently from engine options."""

    speed: float = 1.0
    pitch_semitones: float = 0.0
    volume_db: float = 0.0

    def __post_init__(self) -> None:
        if not 0.5 <= self.speed <= 2.0:
            raise ValidationError("Tốc độ đọc phải nằm trong khoảng 0.5x đến 2.0x.")
        if not -12.0 <= self.pitch_semitones <= 12.0:
            raise ValidationError("Cao độ phải nằm trong khoảng -12 đến +12 semitone.")


@dataclass(frozen=True)
class SynthesisRequest:
    """Input for the synthesize-speech use case."""

    text: str
    engine_id: str
    options: EngineSynthesisOptions
    effects: AudioEffects


@dataclass(frozen=True)
class SynthesisResult:
    """Engine-neutral mono floating-point audio and its sample rate."""

    audio: np.ndarray
    sample_rate: int

    def __post_init__(self) -> None:
        if not isinstance(self.audio, np.ndarray):
            raise ValidationError("Dữ liệu âm thanh phải là NumPy array.")
        if self.audio.ndim != 1:
            raise ValidationError("Dữ liệu âm thanh phải là mảng một chiều.")
        if self.sample_rate <= 0:
            raise ValidationError("Sample rate phải lớn hơn 0.")


@dataclass(frozen=True)
class HardwareInfo:
    """Local hardware facts relevant to selecting an engine."""

    cpu_name: str
    physical_cores: int
    logical_cores: int
    ram_gb: float
    gpu_name: str | None
    vram_gb: float | None
    cuda_available: bool
    operating_system: str
    architecture: str

    def __post_init__(self) -> None:
        if self.physical_cores < 0 or self.logical_cores < 0:
            raise ValidationError("Số lượng lõi CPU không được âm.")
        if self.ram_gb < 0:
            raise ValidationError("Dung lượng RAM không được âm.")
        if self.vram_gb is not None and self.vram_gb < 0:
            raise ValidationError("Dung lượng VRAM không được âm.")


@dataclass(frozen=True)
class EngineRecommendation:
    """An explainable, non-binding engine recommendation."""

    engine_id: str
    reason: str
    confidence: str

    def __post_init__(self) -> None:
        if self.confidence not in {"high", "medium", "low"}:
            raise ValidationError("Độ tin cậy phải là high, medium hoặc low.")


@dataclass(frozen=True)
class TierSettings:
    """Configurable resource threshold for one hardware tier."""

    min_ram_gb: float
    min_physical_cores: int
    min_vram_gb: float | None = None


@dataclass(frozen=True)
class HardwareRecommendationSettings:
    """Domain policy parameters loaded by the outer configuration layer."""

    high_tier: TierSettings
    medium_tier: TierSettings
