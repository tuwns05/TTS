"""Contract tests for the local-only Kokoro-Vietnamese adapter."""

from pathlib import Path

import numpy as np
import pytest

from vntts.db.models import EngineSynthesisOptions
from vntts.engines.kokoro_engine import KokoroVIEngine
from vntts.utils.exceptions import EngineLoadError, ValidationError


class _KokoroRuntime:
    def __init__(self) -> None:
        self.closed = False

    def synthesize(self, text: str) -> tuple[np.ndarray, str]:
        return np.ones(len(text), dtype=np.float64), "phonemes"

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def kokoro_assets(tmp_path: Path) -> tuple[Path, Path, Path]:
    model = tmp_path / "kokoro_vi.pth"
    config = tmp_path / "config.json"
    voices = tmp_path / "voicepacks"
    model.write_bytes(b"model")
    config.write_text("{}", encoding="utf-8")
    voices.mkdir()
    (voices / "diem_trinh.pt").write_bytes(b"voice")
    (voices / "mai_linh.pt").write_bytes(b"voice")
    return model, config, voices


def test_kokoro_passes_complete_local_paths_and_runs_on_cpu(
    kokoro_assets: tuple[Path, Path, Path],
) -> None:
    calls: list[dict[str, object]] = []

    def factory(**kwargs: object) -> _KokoroRuntime:
        calls.append(kwargs)
        return _KokoroRuntime()

    model, config, voices = kokoro_assets
    engine = KokoroVIEngine(model, config, voices, sdk_factory=factory)
    engine.load("auto")

    assert calls[0] == {
        "device": "cpu",
        "voice": "diem_trinh",
        "model_path": str(model.resolve()),
        "voicepack_path": str((voices / "diem_trinh.pt").resolve()),
        "config_path": str(config.resolve()),
    }
    assert {voice.voice_id for voice in engine.list_voices()} == {
        "diem_trinh",
        "mai_linh",
    }
    result = engine.synthesize("Xin chào", EngineSynthesisOptions("mai_linh"))
    assert calls[-1]["voice"] == "mai_linh"
    assert result.audio.dtype == np.float32
    assert result.sample_rate == 24_000


def test_kokoro_requires_local_voicepack(tmp_path: Path) -> None:
    model = tmp_path / "kokoro_vi.pth"
    config = tmp_path / "config.json"
    model.write_bytes(b"model")
    config.write_text("{}", encoding="utf-8")
    engine = KokoroVIEngine(
        model,
        config,
        tmp_path / "voicepacks",
        sdk_factory=lambda **_: _KokoroRuntime(),
    )

    assert not engine.is_available()
    with pytest.raises(EngineLoadError, match="voicepack"):
        engine.load("cpu")


def test_kokoro_rejects_cuda_and_voice_cloning(
    kokoro_assets: tuple[Path, Path, Path],
) -> None:
    model, config, voices = kokoro_assets
    engine = KokoroVIEngine(
        model,
        config,
        voices,
        sdk_factory=lambda **_: _KokoroRuntime(),
    )
    with pytest.raises(EngineLoadError, match="chỉ hỗ trợ CPU"):
        engine.load("cuda")

    engine.load("cpu")
    with pytest.raises(ValidationError, match="không hỗ trợ Voice Cloning"):
        engine.synthesize(
            "Xin chào",
            EngineSynthesisOptions("diem_trinh", "reference.wav"),
        )


def test_kokoro_capabilities_are_voicepack_cpu_only() -> None:
    capabilities = KokoroVIEngine.CAPABILITIES
    assert capabilities.cpu_supported
    assert not capabilities.gpu_supported
    assert not capabilities.voice_cloning
    assert not capabilities.streaming
