"""Tests for best-effort local hardware detection."""

import importlib

from vntts.db.models import HardwareInfo
from vntts.services.hardware import HardwareDetector


def test_detector_always_returns_hardware_info() -> None:
    result = HardwareDetector().detect()

    assert isinstance(result, HardwareInfo)
    assert result.physical_cores >= 0
    assert result.logical_cores >= 0
    assert result.ram_gb >= 0


def test_detector_survives_missing_torch(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    real_import = importlib.import_module

    def import_without_torch(name: str, package: str | None = None):  # type: ignore[no-untyped-def]
        if name == "torch":
            raise ImportError("torch intentionally unavailable")
        return real_import(name, package)

    monkeypatch.setattr(importlib, "import_module", import_without_torch)

    result = HardwareDetector().detect()

    assert result.cuda_available is False
    assert result.gpu_name is None
    assert result.vram_gb is None
