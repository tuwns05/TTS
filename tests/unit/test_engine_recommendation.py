"""Tests for configurable hardware recommendation rules."""

import pytest

from vntts.services.hardware import (
    EngineRecommendationService,
)
from vntts.config.settings import Settings
from vntts.db.models import HardwareInfo


def _hardware(
    *,
    cores: int,
    ram: float,
    cuda: bool = False,
    vram: float | None = None,
) -> HardwareInfo:
    return HardwareInfo(
        cpu_name="Test CPU",
        physical_cores=cores,
        logical_cores=cores * 2,
        ram_gb=ram,
        gpu_name="Test GPU" if cuda else None,
        vram_gb=vram,
        cuda_available=cuda,
        operating_system="TestOS",
        architecture="x86_64",
    )


@pytest.mark.parametrize(
    ("hardware", "expected_id", "expected_confidence"),
    [
        (_hardware(cores=4, ram=8, cuda=True, vram=6), "vieneu-v3", "high"),
        (_hardware(cores=6, ram=16), "vieneu-v3", "medium"),
        (_hardware(cores=4, ram=8), "vieneu-v2", "medium"),
        (_hardware(cores=2, ram=4), "kokoro-vi", "high"),
    ],
)
def test_recommendation_tiers(
    settings: Settings,
    hardware: HardwareInfo,
    expected_id: str,
    expected_confidence: str,
) -> None:
    service = EngineRecommendationService(settings.hardware_recommendation)

    recommendation = service.recommend(hardware)

    assert recommendation.engine_id == expected_id
    assert recommendation.confidence == expected_confidence
    assert recommendation.reason.strip()
