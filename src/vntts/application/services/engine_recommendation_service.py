"""Explainable, configurable engine recommendation policy."""

from vntts.domain.hardware.models import (
    EngineRecommendation,
    HardwareInfo,
    HardwareRecommendationSettings,
)
from vntts.domain.tts.models import (
    KOKORO_VI_ENGINE_ID,
    VIENEU_V2_ENGINE_ID,
    VIENEU_V3_ENGINE_ID,
)


class EngineRecommendationService:
    """Recommend an engine without loading it or overriding user choice."""

    def __init__(self, thresholds: HardwareRecommendationSettings) -> None:
        self._thresholds = thresholds

    def recommend(self, hardware: HardwareInfo) -> EngineRecommendation:
        """Return an engine recommendation and a Vietnamese explanation."""

        high = self._thresholds.high_tier
        medium = self._thresholds.medium_tier
        gpu_is_high_tier = (
            hardware.cuda_available
            and hardware.vram_gb is not None
            and high.min_vram_gb is not None
            and hardware.vram_gb >= high.min_vram_gb
        )
        if gpu_is_high_tier:
            return EngineRecommendation(
                engine_id=VIENEU_V3_ENGINE_ID,
                reason="Phát hiện GPU CUDA và tài nguyên phù hợp với engine chất lượng cao.",
                confidence="high",
            )

        cpu_is_high_tier = (
            hardware.ram_gb >= high.min_ram_gb
            and hardware.physical_cores >= high.min_physical_cores
        )
        if cpu_is_high_tier:
            return EngineRecommendation(
                engine_id=VIENEU_V3_ENGINE_ID,
                reason="CPU và RAM đạt ngưỡng cấu hình tầng cao; có thể thử VieNeu-TTS v3.",
                confidence="medium",
            )

        cpu_is_medium_tier = (
            hardware.ram_gb >= medium.min_ram_gb
            and hardware.physical_cores >= medium.min_physical_cores
        )
        if cpu_is_medium_tier:
            return EngineRecommendation(
                engine_id=VIENEU_V2_ENGINE_ID,
                reason="CPU và RAM phù hợp với cấu hình tầm trung.",
                confidence="medium",
            )

        return EngineRecommendation(
            engine_id=KOKORO_VI_ENGINE_ID,
            reason="Tài nguyên hiện có phù hợp hơn với engine CPU nhẹ.",
            confidence="high",
        )
