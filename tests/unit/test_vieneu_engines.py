"""Contract tests for VieNeu adapters without loading real models."""

import warnings
from pathlib import Path

import numpy as np
import pytest

import vntts.engines.vieneu_engine as vieneu_module
from vntts.db.models import EngineSynthesisOptions
from vntts.engines.vieneu_engine import VieNeuV2Engine, VieNeuV3Engine
from vntts.utils.exceptions import EngineLoadError, ValidationError


class _VieNeuRuntime:
    def __init__(self) -> None:
        self.closed = False

    def list_preset_voices(self) -> list[tuple[str, str]]:
        return [
            (
                "Bác sĩ Tuyền — Nữ · Bắc · Phong cách tin tức",
                "bac_si_tuyen",
            )
        ]

    def get_preset_voice(self, voice_name: str) -> object:
        return {"id": voice_name}

    def infer(self, **kwargs: object) -> np.ndarray:
        text = str(kwargs["text"])
        return np.linspace(-0.2, 0.2, len(text) + 1, dtype=np.float64)

    def encode_reference(
        self, ref_audio: str, denoise: bool = True
    ) -> tuple[np.ndarray, np.ndarray]:
        return (
            np.array([0.1, -0.2], dtype=np.float32),
            np.array([[1, 2, 3]], dtype=np.int64),
        )

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def vieneu_paths(tmp_path: Path) -> tuple[Path, Path]:
    backbone = tmp_path / "backbone"
    codec = tmp_path / "codec"
    backbone.mkdir()
    codec.mkdir()
    return backbone, codec


def test_vieneu_v2_load_uses_only_local_paths(
    vieneu_paths: tuple[Path, Path],
) -> None:
    calls: list[dict[str, object]] = []
    runtime = _VieNeuRuntime()

    def factory(**kwargs: object) -> _VieNeuRuntime:
        calls.append(kwargs)
        return runtime

    backbone, codec = vieneu_paths
    engine = VieNeuV2Engine(backbone, codec, sdk_factory=factory)
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
    assert engine.list_voices()[0].display_name == "Bác sĩ Tuyền — Nữ · Bắc"
    result = engine.synthesize("Xin chào", EngineSynthesisOptions("bac_si_tuyen"))
    assert result.audio.dtype == np.float32
    assert result.audio.ndim == 1

    engine.unload()
    assert runtime.closed


def test_vieneu_v3_loads_from_local_model_directory(tmp_path: Path) -> None:
    calls: list[dict[str, object]] = []
    runtime = _VieNeuRuntime()
    model_path = tmp_path / "vieneu-v3"
    model_path.mkdir()
    tokenizer_path = model_path / "moss-tokenizer"
    tokenizer_path.mkdir()

    def factory(**kwargs: object) -> _VieNeuRuntime:
        calls.append(kwargs)
        return runtime

    engine = VieNeuV3Engine(
        model_path,
        tokenizer_path=tokenizer_path,
        sdk_factory=factory,
    )
    engine.load("cpu")

    assert calls == [
        {
            "mode": "v3turbo",
            "backbone_repo": str(model_path.resolve()),
            "moss_tokenizer": str(tokenizer_path.resolve()),
            "device": "cpu",
            "backend": "onnx",
        }
    ]
    assert engine.list_voices()[0].voice_id == "bac_si_tuyen"
    assert engine.runtime_info is not None
    assert engine.runtime_info.device == "cpu"
    assert engine.runtime_info.backend == "onnx"
    engine.unload()
    assert runtime.closed


def test_vieneu_v3_gpu_uses_pytorch_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model_path = tmp_path / "vieneu-v3"
    tokenizer_path = model_path / "moss-tokenizer"
    tokenizer_path.mkdir(parents=True)
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(vieneu_module, "_cuda_available", lambda: True)
    monkeypatch.setattr(VieNeuV3Engine, "_device_name", lambda self, device: "Test GPU")

    engine = VieNeuV3Engine(
        model_path,
        tokenizer_path=tokenizer_path,
        sdk_factory=lambda **kwargs: calls.append(kwargs) or _VieNeuRuntime(),
    )
    engine.load("cuda")

    assert calls[0]["device"] == "cuda"
    assert calls[0]["backend"] == "pytorch"
    assert engine.runtime_info is not None
    assert engine.runtime_info.is_gpu
    assert engine.runtime_info.device_name == "Test GPU"


def test_vieneu_v3_explicit_gpu_reports_missing_cuda(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model_path = tmp_path / "vieneu-v3"
    tokenizer_path = model_path / "moss-tokenizer"
    tokenizer_path.mkdir(parents=True)
    monkeypatch.setattr(vieneu_module, "_cuda_available", lambda: False)
    engine = VieNeuV3Engine(
        model_path,
        tokenizer_path=tokenizer_path,
        sdk_factory=lambda **_: _VieNeuRuntime(),
    )

    with pytest.raises(EngineLoadError, match="GPU NVIDIA/CUDA"):
        engine.load("cuda")


def test_vieneu_v3_auto_falls_back_to_onnx_cpu_when_gpu_load_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model_path = tmp_path / "vieneu-v3"
    tokenizer_path = model_path / "moss-tokenizer"
    tokenizer_path.mkdir(parents=True)
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(vieneu_module, "_cuda_available", lambda: True)

    def factory(**kwargs: object) -> _VieNeuRuntime:
        calls.append(kwargs)
        if kwargs["device"] == "cuda":
            raise RuntimeError("CUDA out of memory")
        return _VieNeuRuntime()

    engine = VieNeuV3Engine(
        model_path,
        tokenizer_path=tokenizer_path,
        sdk_factory=factory,
    )
    engine.load("auto")

    assert [(call["device"], call["backend"]) for call in calls] == [
        ("cuda", "pytorch"),
        ("cpu", "onnx"),
    ]
    assert engine.runtime_info is not None
    assert engine.runtime_info.device == "cpu"
    assert engine.runtime_info.fallback_reason is not None


def test_vieneu_v3_development_can_use_official_repository() -> None:
    calls: list[dict[str, object]] = []

    def factory(**kwargs: object) -> _VieNeuRuntime:
        calls.append(kwargs)
        return _VieNeuRuntime()

    engine = VieNeuV3Engine(allow_download=True, sdk_factory=factory)
    assert engine.is_available()
    engine.load("cpu")

    assert calls[0]["mode"] == "v3turbo"
    assert calls[0]["backbone_repo"] == "pnnbao-ump/VieNeu-TTS-v3-Turbo"
    assert calls[0]["moss_tokenizer"] == "OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano"


def test_vieneu_rejects_missing_local_assets(tmp_path: Path) -> None:
    engine = VieNeuV3Engine(
        tmp_path / "missing-model",
        sdk_factory=lambda **_: _VieNeuRuntime(),
    )

    assert not engine.is_available()
    with pytest.raises(EngineLoadError, match="Thiếu tài nguyên VieNeu v3 bundled"):
        engine.load("cpu")


def test_vieneu_v3_passes_local_reference_audio(
    tmp_path: Path,
) -> None:
    model_path = tmp_path / "vieneu-v3"
    model_path.mkdir()
    tokenizer_path = model_path / "moss-tokenizer"
    tokenizer_path.mkdir()
    calls: list[dict[str, object]] = []

    class Runtime(_VieNeuRuntime):
        def infer(self, **kwargs: object) -> np.ndarray:
            calls.append(kwargs)
            warnings.warn(
                "In 2.9, this function's implementation will be changed to use "
                "torchaudio.load_with_torchcodec under the hood.",
                UserWarning,
            )
            return super().infer(**kwargs)

    engine = VieNeuV3Engine(
        model_path,
        tokenizer_path=tokenizer_path,
        sdk_factory=lambda **_: Runtime(),
    )
    engine.load("cpu")
    reference = tmp_path / "reference.wav"
    reference.write_bytes(b"audio")

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        result = engine.synthesize(
            "Xin chào",
            EngineSynthesisOptions("clone:test-profile", str(reference)),
        )

    assert calls[-1] == {
        "text": "Xin chào",
        "ref_audio": str(reference.resolve()),
        "style": "tu_nhien",
    }
    assert result.sample_rate == 48_000
    assert captured == []


def test_vieneu_v3_only_passes_supported_arguments_to_runtime(tmp_path: Path) -> None:
    model_path = tmp_path / "vieneu-v3"
    model_path.mkdir()
    tokenizer_path = model_path / "moss-tokenizer"
    tokenizer_path.mkdir()
    calls: list[dict[str, object]] = []

    class Runtime(_VieNeuRuntime):
        def infer(self, **kwargs: object) -> np.ndarray:
            calls.append(kwargs)
            return super().infer(**kwargs)

    engine = VieNeuV3Engine(
        model_path,
        tokenizer_path=tokenizer_path,
        sdk_factory=lambda **_: Runtime(),
    )
    engine.load("cpu")

    engine.synthesize("Xin chào", EngineSynthesisOptions("bac_si_tuyen"))

    assert calls[-1] == {
        "text": "Xin chào",
        "voice": {"id": "bac_si_tuyen"},
        "style": "tu_nhien",
    }


def test_vieneu_v3_uses_saved_features_without_reference_audio(tmp_path: Path) -> None:
    model_path = tmp_path / "vieneu-v3"
    model_path.mkdir()
    tokenizer_path = model_path / "moss-tokenizer"
    tokenizer_path.mkdir()
    calls: list[dict[str, object]] = []

    class Runtime(_VieNeuRuntime):
        def infer(self, **kwargs: object) -> np.ndarray:
            calls.append(kwargs)
            return super().infer(**kwargs)

    engine = VieNeuV3Engine(
        model_path,
        tokenizer_path=tokenizer_path,
        sdk_factory=lambda **_: Runtime(),
    )
    engine.load("cpu")
    artifact = tmp_path / "voice.npz"
    speaker = np.array([0.1, 0.2], dtype=np.float32)
    codes = np.array([[7, 8]], dtype=np.int64)
    np.savez_compressed(artifact, speaker_emb=speaker, ref_codes=codes)

    engine.synthesize(
        "Xin chào",
        EngineSynthesisOptions(
            "clone:profile",
            voice_artifact_path=str(artifact),
        ),
    )

    assert "ref_audio" not in calls[-1]
    voice = calls[-1]["voice"]
    assert isinstance(voice, dict)
    np.testing.assert_allclose(voice["speaker_emb"], speaker)
    np.testing.assert_array_equal(voice["codes"], codes)


def test_vieneu_v3_extracts_reusable_features_once(tmp_path: Path) -> None:
    model_path = tmp_path / "vieneu-v3"
    model_path.mkdir()
    tokenizer_path = model_path / "moss-tokenizer"
    tokenizer_path.mkdir()
    calls: list[tuple[str, bool]] = []

    class Runtime(_VieNeuRuntime):
        def encode_reference(
            self, ref_audio: str, denoise: bool = True
        ) -> tuple[np.ndarray, np.ndarray]:
            calls.append((ref_audio, denoise))
            return super().encode_reference(ref_audio, denoise)

    engine = VieNeuV3Engine(
        model_path,
        tokenizer_path=tokenizer_path,
        sdk_factory=lambda **_: Runtime(),
    )
    engine.load("cpu")
    reference = tmp_path / "temporary.wav"
    reference.write_bytes(b"audio")

    speaker, codes = engine.encode_voice_reference(str(reference))

    assert calls == [(str(reference.resolve()), True)]
    assert speaker.dtype == np.float32
    assert codes.dtype == np.int64


def test_vieneu_v3_passes_selected_speaking_style(tmp_path: Path) -> None:
    model_path = tmp_path / "vieneu-v3"
    model_path.mkdir()
    tokenizer_path = model_path / "moss-tokenizer"
    tokenizer_path.mkdir()
    calls: list[dict[str, object]] = []

    class Runtime(_VieNeuRuntime):
        def infer(self, **kwargs: object) -> np.ndarray:
            calls.append(kwargs)
            return super().infer(**kwargs)

    engine = VieNeuV3Engine(
        model_path,
        tokenizer_path=tokenizer_path,
        sdk_factory=lambda **_: Runtime(),
    )
    engine.load("cpu")

    engine.synthesize(
        "Bản tin hôm nay",
        EngineSynthesisOptions("bac_si_tuyen", style_id="tin_tuc"),
    )

    assert calls[-1]["style"] == "tin_tuc"


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


def test_capabilities_match_adapter_contract() -> None:
    assert VieNeuV3Engine.CAPABILITIES.cpu_supported
    assert VieNeuV3Engine.CAPABILITIES.gpu_supported
    assert VieNeuV3Engine.CAPABILITIES.voice_cloning
    assert VieNeuV3Engine.CAPABILITIES.supported_style_ids == (
        "tu_nhien",
        "tin_tuc",
        "doc_truyen",
    )
    assert not VieNeuV2Engine.CAPABILITIES.gpu_supported
    assert not VieNeuV2Engine.CAPABILITIES.streaming
