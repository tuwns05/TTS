"""Create or validate the pinned VieNeu v3 offline model bundle."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from vntts.engines.model_bundle import validate_vieneu_v3_bundle

SDK_VERSION = "3.2.4"


@dataclass(frozen=True)
class RepositorySnapshot:
    repo_id: str
    revision: str
    files: tuple[str, ...]


SNAPSHOTS = (
    RepositorySnapshot(
        "pnnbao-ump/VieNeu-TTS-v3-Turbo",
        "75ff82a72f54d55ed389e1eeb12041d3c4bac7d4",
        (
            "config.json",
            "denoiser.onnx",
            "speaker_encoder.onnx",
            "onnx_int8/config.json",
            "onnx_int8/tokenizer.json",
            "onnx_int8/vieneu_acoustic_cached.onnx",
            "onnx_int8/vieneu_backbone_shared.data",
            "onnx_int8/vieneu_decode_step.onnx",
            "onnx_int8/vieneu_prefill.onnx",
            "onnx_int8/vieneu_v3_heads.npz",
            "update/config.json",
            "update/model.safetensors",
            "update/special_tokens_map.json",
            "update/tokenizer.json",
            "update/tokenizer_config.json",
        ),
    ),
    RepositorySnapshot(
        "OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano",
        "6aa02b01e445cc585582cf0ba480bc3ea6c8dd68",
        (
            "config.json",
            "configuration_moss_audio_tokenizer.py",
            "model-00001-of-00001.safetensors",
            "model.safetensors.index.json",
            "modeling_moss_audio_tokenizer.py",
        ),
    ),
    RepositorySnapshot(
        "OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX",
        "ceff0d0749bfb3fa2d61149794ec6feef0d1e1ae",
        (
            "codec_browser_onnx_meta.json",
            "moss_audio_tokenizer_decode_full.onnx",
            "moss_audio_tokenizer_decode_shared.data",
            "moss_audio_tokenizer_decode_step.onnx",
            "moss_audio_tokenizer_encode.data",
            "moss_audio_tokenizer_encode.onnx",
        ),
    ),
)


def _cache_name(repo_id: str) -> str:
    return "models--" + repo_id.replace("/", "--")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_snapshot(
    snapshot: RepositorySnapshot,
    hub_root: Path,
    *,
    local_files_only: bool,
) -> None:
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise SystemExit("Cần cài huggingface-hub để chuẩn bị model.") from exc

    source = Path(
        snapshot_download(
            repo_id=snapshot.repo_id,
            revision=snapshot.revision,
            allow_patterns=list(snapshot.files),
            local_files_only=local_files_only,
        )
    )
    repo_root = hub_root / _cache_name(snapshot.repo_id)
    destination = repo_root / "snapshots" / snapshot.revision
    destination.mkdir(parents=True, exist_ok=True)
    for relative in snapshot.files:
        source_file = source / relative
        if not source_file.is_file():
            raise SystemExit(
                f"Snapshot {snapshot.repo_id}@{snapshot.revision} thiếu {relative}."
            )
        target_file = destination / relative
        target_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, target_file)
    refs = repo_root / "refs"
    refs.mkdir(parents=True, exist_ok=True)
    (refs / "main").write_text(snapshot.revision, encoding="utf-8")


def _write_manifest(bundle_root: Path) -> None:
    files = []
    for path in sorted((bundle_root / "hub").rglob("*")):
        if path.is_file():
            files.append(
                {
                    "path": path.relative_to(bundle_root).as_posix(),
                    "size": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )
    manifest = {
        "schema_version": 1,
        "engine_id": "vieneu-v3",
        "sdk_version": SDK_VERSION,
        "backend": "pytorch-cuda+onnx-int8-cpu",
        "hub_cache": "hub",
        "repositories": [
            {"repo_id": item.repo_id, "revision": item.revision}
            for item in SNAPSHOTS
        ],
        "files": files,
    }
    (bundle_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def prepare(destination: Path, *, local_files_only: bool) -> None:
    if importlib.metadata.version("vieneu") != SDK_VERSION:
        raise SystemExit(f"Script yêu cầu vieneu=={SDK_VERSION}.")
    if destination.exists():
        raise SystemExit(
            f"Bundle đã tồn tại tại {destination}. Xóa có chủ đích trước khi tạo lại."
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".vieneu-v3-", dir=destination.parent))
    try:
        hub_root = staging / "hub"
        for snapshot in SNAPSHOTS:
            print(f"Chuẩn bị {snapshot.repo_id}@{snapshot.revision}...")
            _copy_snapshot(snapshot, hub_root, local_files_only=local_files_only)
        _write_manifest(staging)
        validate_vieneu_v3_bundle(staging, verify_hashes=True)
        staging.replace(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--destination",
        type=Path,
        default=REPOSITORY_ROOT / "resources" / "models" / "vieneu-v3",
    )
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--skip-hashes", action="store_true")
    args = parser.parse_args()
    destination = args.destination.expanduser().resolve()
    if args.validate_only:
        info = validate_vieneu_v3_bundle(
            destination,
            verify_hashes=not args.skip_hashes,
        )
        print(f"Bundle hợp lệ: {info.root}")
        return 0
    prepare(destination, local_files_only=args.local_files_only)
    print(f"Đã tạo bundle VieNeu v3: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
