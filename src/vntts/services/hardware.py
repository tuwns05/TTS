"""Local hardware detection and configurable engine recommendation."""

from __future__ import annotations

import importlib
import platform

import cpuinfo
import psutil
from loguru import logger

from vntts.db.models import (
    EngineRecommendation,
    HardwareInfo,
    HardwareRecommendationSettings,
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


class HardwareDetector:
    """Collect local hardware facts without network access or mandatory CUDA."""

    def detect(self) -> HardwareInfo:
        """Return best-effort hardware information and safe fallbacks."""

        cpu_name = platform.processor() or "Không xác định"
        try:
            details = cpuinfo.get_cpu_info()
            cpu_name = str(details.get("brand_raw") or cpu_name)
        except Exception as exc:
            logger.debug("Không đọc được tên CPU chi tiết: {}", type(exc).__name__)

        try:
            physical_cores = psutil.cpu_count(logical=False) or 0
            logical_cores = psutil.cpu_count(logical=True) or physical_cores
            ram_gb = psutil.virtual_memory().total / (1024**3)
        except Exception as exc:
            logger.warning("Không đọc được đầy đủ CPU/RAM: {}", type(exc).__name__)
            physical_cores = 0
            logical_cores = 0
            ram_gb = 0.0

        gpu_name, vram_gb, cuda_available = self._detect_cuda()
        return HardwareInfo(
            cpu_name=cpu_name,
            physical_cores=physical_cores,
            logical_cores=logical_cores,
            ram_gb=round(ram_gb, 2),
            gpu_name=gpu_name,
            vram_gb=None if vram_gb is None else round(vram_gb, 2),
            cuda_available=cuda_available,
            operating_system=platform.system(),
            architecture=platform.machine(),
        )

    @staticmethod
    def _detect_cuda() -> tuple[str | None, float | None, bool]:
        try:
            torch = importlib.import_module("torch")
        except ImportError:
            return None, None, False
        except Exception as exc:
            logger.debug("Không thể import PyTorch tùy chọn: {}", type(exc).__name__)
            return None, None, False

        try:
            if not bool(torch.cuda.is_available()):
                return None, None, False
            device_index = int(torch.cuda.current_device())
            gpu_name = str(torch.cuda.get_device_name(device_index))
            properties = torch.cuda.get_device_properties(device_index)
            vram_gb = float(properties.total_memory) / (1024**3)
            return gpu_name, vram_gb, True
        except Exception as exc:
            logger.debug("Không thể đọc thông tin CUDA: {}", type(exc).__name__)
            return None, None, False
