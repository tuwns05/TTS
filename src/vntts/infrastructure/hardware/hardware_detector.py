"""Best-effort local hardware detection with optional PyTorch support."""

from __future__ import annotations

import importlib
import platform

import cpuinfo
import psutil
from loguru import logger

from vntts.domain.hardware.models import HardwareInfo


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
