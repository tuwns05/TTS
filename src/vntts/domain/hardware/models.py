"""Hardware and recommendation value objects."""

from dataclasses import dataclass

from vntts.domain.exceptions import ValidationError


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
