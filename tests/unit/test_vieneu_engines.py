"""Contract tests for local-only VieNeu adapters without real models."""

from pathlib import Path

import numpy as np
import pytest

from vntts.db.models import EngineSynthesisOptions
from vntts.engines.vieneu_engine import VieNeuV2Engine, VieNeuV3Engine
from vntts.utils.exceptions import EngineLoadError, ValidationError


class _VieNeuRuntime:
    def __init__(self) -> None:
        self.closed = False

    def list_preset_voices(self) -> list[tuple[str, str]]:
        return [("Bác sĩ Tuyền", "bac_si_tuyen")]

    def get_preset_voice(self, voice_name: str) -> object:
        return {"id": voice_name}

    def infer(self, **kwargs: object) -> np.ndarray:
        text = str(kwargs["text"])
        return np.linspace(-0.2, 0.2, len(text) + 1, dtype=np.float64)

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def vieneu_paths(tmp_path: Path) -> tuple[Path, Path]:
    backbone = tmp_path / "backbone"
    codec = tmp_path / "codec"
    backbone.mkdir()
    codec.mkdir()
    return backbone, codec


@pytest.mark.parametrize("engine_class", [VieNeuV3Engine, VieNeuV2Engine])
def test_vieneu_load_uses_only_local_paths(
    engine_class: type[VieNeuV3Engine] | type[VieNeuV2Engine],
    vieneu_paths: tuple[Path, Path],
) -> None:
    calls: list[dict[str, object]] = []
    runtime = _VieNeuRuntime()

    def factory(**kwargs: object) -> _VieNeuRuntime:
        calls.append(kwargs)
        return runtime

    backbone, codec = vieneu_paths
    engine = engine_class(backbone, codec, sdk_factory=factory)
    engine.load("cpu")

    assert calls == [
        {
            "mode": "standard",
            "backbone_repo": str(backbone.resolve()),
            "backbone_device": "cpu",
            "codec_repo": str(codec.resolve()),
            "codec_device": "cpu",
        }
    ]
    assert engine.list_voices()[0].voice_id == "bac_si_tuyen"
    result = engine.synthesize("Xin chào", EngineSynthesisOptions("bac_si_tuyen"))
    assert result.audio.dtype == np.float32
    assert result.audio.ndim == 1

    engine.unload()
    assert runtime.closed


def test_vieneu_rejects_missing_local_assets(tmp_path: Path) -> None:
    engine = VieNeuV3Engine(
        tmp_path / "missing-backbone",
        tmp_path / "missing-codec",
        sdk_factory=lambda **_: _VieNeuRuntime(),
    )

    assert not engine.is_available()
    with pytest.raises(EngineLoadError, match="Thiếu model VieNeu local"):
        engine.load("cpu")


def test_vieneu_v3_passes_local_reference_audio(
    vieneu_paths: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    backbone, codec = vieneu_paths
    calls: list[dict[str, object]] = []

    class Runtime(_VieNeuRuntime):
        def infer(self, **kwargs: object) -> np.ndarray:
            calls.append(kwargs)
            return super().infer(**kwargs)

    engine = VieNeuV3Engine(
        backbone,
        codec,
        sdk_factory=lambda **_: Runtime(),
    )
    engine.load("cpu")
    reference = tmp_path / "reference.wav"
    reference.write_bytes(b"audio")

    result = engine.synthesize(
        "Xin chào",
        EngineSynthesisOptions("bac_si_tuyen", str(reference)),
    )

    assert calls[-1] == {
        "text": "Xin chào",
        "ref_audio": str(reference.resolve()),
    }
    assert result.sample_rate == 48_000


def test_vieneu_v2_rejects_reference_audio(
    vieneu_paths: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    backbone, codec = vieneu_paths
    reference = tmp_path / "reference.wav"
    reference.write_bytes(b"audio")
    engine = VieNeuV2Engine(
        backbone,
        codec,
        sdk_factory=lambda **_: _VieNeuRuntime(),
    )
    engine.load("cpu")

    with pytest.raises(ValidationError, match="không hỗ trợ Voice Cloning"):
        engine.synthesize(
            "Xin chào",
            EngineSynthesisOptions("bac_si_tuyen", str(reference)),
        )


def test_capabilities_match_phase_2_adapter_contract() -> None:
    assert VieNeuV3Engine.CAPABILITIES.cpu_supported
    assert VieNeuV3Engine.CAPABILITIES.gpu_supported
    assert VieNeuV3Engine.CAPABILITIES.voice_cloning
    assert not VieNeuV2Engine.CAPABILITIES.gpu_supported
    assert not VieNeuV2Engine.CAPABILITIES.streaming
