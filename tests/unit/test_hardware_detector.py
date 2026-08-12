"""Tests for best-effort local hardware detection."""

import subprocess

from vntts.db.models import HardwareInfo
from vntts.services.hardware import HardwareDetector


def test_detector_always_returns_hardware_info() -> None:
    result = HardwareDetector().detect()

    assert isinstance(result, HardwareInfo)
    assert result.physical_cores >= 0
    assert result.logical_cores >= 0
    assert result.ram_gb >= 0


def test_detector_survives_missing_nvidia_driver(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def missing_nvidia_smi(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise FileNotFoundError("nvidia-smi intentionally unavailable")

    monkeypatch.setattr(subprocess, "run", missing_nvidia_smi)

    result = HardwareDetector().detect()

    assert result.cuda_available is False
    assert result.gpu_name is None
    assert result.vram_gb is None


def test_detector_reads_nvidia_gpu_without_importing_torch(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def nvidia_smi(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="NVIDIA GeForce RTX 4050 Laptop GPU, 6144\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", nvidia_smi)

    result = HardwareDetector().detect()

    assert result.cuda_available is True
    assert result.gpu_name == "NVIDIA GeForce RTX 4050 Laptop GPU"
    assert result.vram_gb == 6.0
