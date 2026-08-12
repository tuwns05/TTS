import hashlib
import json
import os
from pathlib import Path

import pytest

from vntts.engines.model_bundle import validate_vieneu_v3_bundle
from vntts.engines.vieneu_engine import (
    VIENEU_V3_REPOSITORY,
    VIENEU_V3_TOKENIZER_REPOSITORY,
    VieNeuV3Engine,
)
from vntts.utils.exceptions import EngineLoadError


def _bundle(tmp_path: Path) -> Path:
    root = tmp_path / "vieneu-v3"
    model = root / "hub" / "model.bin"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"real-model-bytes")
    manifest = {
        "schema_version": 1,
        "engine_id": "vieneu-v3",
        "sdk_version": "3.2.4",
        "hub_cache": "hub",
        "files": [
            {
                "path": "hub/model.bin",
                "size": model.stat().st_size,
                "sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
            }
        ],
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def test_validate_model_bundle(tmp_path: Path) -> None:
    root = _bundle(tmp_path)

    info = validate_vieneu_v3_bundle(root)

    assert info.hub_cache == (root / "hub").resolve()
    assert info.sdk_version == "3.2.4"


def test_validate_model_bundle_rejects_tampering(tmp_path: Path) -> None:
    root = _bundle(tmp_path)
    (root / "hub" / "model.bin").write_bytes(b"tampered-model")

    with pytest.raises(EngineLoadError, match="sai kích thước|Checksum"):
        validate_vieneu_v3_bundle(root)


def test_engine_uses_pinned_offline_hub_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _bundle(tmp_path)
    calls: list[dict[str, object]] = []

    class Runtime:
        def list_preset_voices(self) -> list[tuple[str, str]]:
            return [("Giọng test", "test")]

        def close(self) -> None:
            return None

    def factory(**kwargs: object) -> Runtime:
        calls.append(kwargs)
        return Runtime()

    monkeypatch.delenv("HF_HUB_CACHE", raising=False)
    engine = VieNeuV3Engine(bundle_path=root, backend="onnx", sdk_factory=factory)
    engine.load("cpu")

    assert calls == [
        {
            "mode": "v3turbo",
            "backbone_repo": VIENEU_V3_REPOSITORY,
            "moss_tokenizer": VIENEU_V3_TOKENIZER_REPOSITORY,
            "device": "cpu",
            "backend": "onnx",
        }
    ]
    assert Path(os.getenv("HF_HUB_CACHE", "")).resolve() == (
        root / "hub"
    ).resolve()
    assert os.getenv("HF_HUB_OFFLINE") == "1"
