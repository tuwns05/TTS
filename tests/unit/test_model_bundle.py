import hashlib
import json
import os
from pathlib import Path

import pytest

import vntts.engines.model_bundle as model_bundle_module
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


def test_validate_model_bundle_reuses_cached_file_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _bundle(tmp_path)
    cache_dir = tmp_path / "cache"
    validate_vieneu_v3_bundle(root, cache_dir=cache_dir)

    def unexpected_hash(_path: Path) -> str:
        raise AssertionError("Không được đọc lại nội dung model khi cache còn hợp lệ")

    monkeypatch.setattr(model_bundle_module, "_sha256", unexpected_hash)

    validate_vieneu_v3_bundle(root, cache_dir=cache_dir)

    marker = json.loads(
        (cache_dir / "vieneu-v3-bundle-validation.json").read_text(encoding="utf-8")
    )
    assert len(marker["manifest_sha256"]) == 64
    assert marker["files"][0]["path"] == "hub/model.bin"
    assert marker["files"][0]["size"] == len(b"real-model-bytes")
    assert isinstance(marker["files"][0]["mtime_ns"], int)


def test_validate_model_bundle_rehashes_when_file_mtime_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _bundle(tmp_path)
    cache_dir = tmp_path / "cache"
    model = root / "hub" / "model.bin"
    validate_vieneu_v3_bundle(root, cache_dir=cache_dir)
    original_hash = model_bundle_module._sha256
    calls: list[Path] = []

    def tracked_hash(path: Path) -> str:
        calls.append(path)
        return original_hash(path)

    current_mtime = model.stat().st_mtime_ns
    os.utime(model, ns=(current_mtime, current_mtime + 1_000_000_000))
    monkeypatch.setattr(model_bundle_module, "_sha256", tracked_hash)

    validate_vieneu_v3_bundle(root, cache_dir=cache_dir)

    assert calls == [model.resolve()]


def test_validate_model_bundle_rehashes_when_manifest_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _bundle(tmp_path)
    cache_dir = tmp_path / "cache"
    manifest_path = root / "manifest.json"
    validate_vieneu_v3_bundle(root, cache_dir=cache_dir)
    original_hash = model_bundle_module._sha256
    calls: list[Path] = []

    def tracked_hash(path: Path) -> str:
        calls.append(path)
        return original_hash(path)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    monkeypatch.setattr(model_bundle_module, "_sha256", tracked_hash)

    validate_vieneu_v3_bundle(root, cache_dir=cache_dir)

    assert calls == [(root / "hub" / "model.bin").resolve()]


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
