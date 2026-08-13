"""Validation and offline cache setup for the bundled VieNeu v3 model."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

from vntts.utils.exceptions import EngineLoadError

VIENEU_V3_BUNDLE_SCHEMA = 1
VIENEU_V3_BUNDLE_ENGINE_ID = "vieneu-v3"


@dataclass(frozen=True)
class ModelBundleInfo:
    """Metadata required by the runtime after a bundle has been validated."""

    root: Path
    hub_cache: Path
    sdk_version: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_vieneu_v3_bundle(
    bundle_root: Path,
    *,
    verify_hashes: bool = True,
    cache_dir: Path | None = None,
) -> ModelBundleInfo:
    """Validate the pinned model manifest without performing network access."""

    root = bundle_root.expanduser().resolve()
    manifest_path = root / "manifest.json"
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EngineLoadError(
            f"Bundle VieNeu v3 thiếu hoặc hỏng manifest: {manifest_path}"
        ) from exc

    if not isinstance(manifest, dict):
        raise EngineLoadError("Manifest VieNeu v3 không phải JSON object hợp lệ.")
    if manifest.get("schema_version") != VIENEU_V3_BUNDLE_SCHEMA:
        raise EngineLoadError("Phiên bản manifest VieNeu v3 không được hỗ trợ.")
    if manifest.get("engine_id") != VIENEU_V3_BUNDLE_ENGINE_ID:
        raise EngineLoadError("Manifest không thuộc engine vieneu-v3.")

    sdk_version = manifest.get("sdk_version")
    if not isinstance(sdk_version, str) or not sdk_version.strip():
        raise EngineLoadError("Manifest VieNeu v3 thiếu phiên bản SDK.")

    hub_cache_name = manifest.get("hub_cache", "hub")
    if not isinstance(hub_cache_name, str) or not hub_cache_name.strip():
        raise EngineLoadError("Manifest VieNeu v3 có đường dẫn hub cache không hợp lệ.")
    hub_cache = (root / hub_cache_name).resolve()
    try:
        hub_cache.relative_to(root)
    except ValueError as exc:
        raise EngineLoadError("Hub cache phải nằm trong bundle VieNeu v3.") from exc
    if not hub_cache.is_dir():
        raise EngineLoadError(f"Bundle VieNeu v3 thiếu hub cache: {hub_cache}")

    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise EngineLoadError("Manifest VieNeu v3 không có danh sách tệp.")

    verified_files: list[dict[str, int | str]] = []
    candidates: list[tuple[Path, str]] = []
    for item in files:
        if not isinstance(item, dict):
            raise EngineLoadError("Manifest VieNeu v3 có mục tệp không hợp lệ.")
        relative = item.get("path")
        expected_size = item.get("size")
        expected_hash = item.get("sha256")
        if (
            not isinstance(relative, str)
            or not relative.strip()
            or not isinstance(expected_size, int)
            or expected_size < 0
            or not isinstance(expected_hash, str)
            or len(expected_hash) != 64
        ):
            raise EngineLoadError("Manifest VieNeu v3 có metadata tệp không hợp lệ.")
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise EngineLoadError("Manifest VieNeu v3 chứa đường dẫn ra ngoài bundle.") from exc
        try:
            file_stat = candidate.stat()
        except OSError as exc:
            raise EngineLoadError(
                f"Tệp model VieNeu v3 thiếu hoặc sai kích thước: {relative}"
            ) from exc
        if not candidate.is_file() or file_stat.st_size != expected_size:
            raise EngineLoadError(f"Tệp model VieNeu v3 thiếu hoặc sai kích thước: {relative}")
        verified_files.append(
            {
                "path": relative,
                "size": file_stat.st_size,
                "mtime_ns": file_stat.st_mtime_ns,
            }
        )
        candidates.append((candidate, expected_hash.lower()))

    if verify_hashes:
        manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
        marker_path = (
            cache_dir.expanduser().resolve() / "vieneu-v3-bundle-validation.json"
            if cache_dir is not None
            else None
        )
        cache_matches = marker_path is not None and _validation_cache_matches(
            marker_path, root, manifest_hash, verified_files
        )
        if not cache_matches:
            for (candidate, expected_hash), item in zip(candidates, files, strict=True):
                if _sha256(candidate) != expected_hash:
                    raise EngineLoadError(
                        f"Checksum model VieNeu v3 không khớp: {item['path']}"
                    )
            if marker_path is not None:
                _write_validation_cache(
                    marker_path, root, manifest_hash, verified_files
                )

    return ModelBundleInfo(root=root, hub_cache=hub_cache, sdk_version=sdk_version)


def _validation_cache_matches(
    marker_path: Path,
    bundle_root: Path,
    manifest_hash: str,
    files: list[dict[str, int | str]],
) -> bool:
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        isinstance(marker, dict)
        and marker.get("bundle_root") == str(bundle_root)
        and marker.get("manifest_sha256") == manifest_hash
        and marker.get("files") == files
    )


def _write_validation_cache(
    marker_path: Path,
    bundle_root: Path,
    manifest_hash: str,
    files: list[dict[str, int | str]],
) -> None:
    marker = {
        "bundle_root": str(bundle_root),
        "manifest_sha256": manifest_hash,
        "files": files,
    }
    temporary_path = marker_path.with_name(f"{marker_path.name}.{os.getpid()}.tmp")
    try:
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path.write_text(
            json.dumps(marker, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(marker_path)
    except OSError:
        # Cache chỉ là tối ưu; lỗi ghi cache không được làm model load thất bại.
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass


def configure_offline_huggingface_cache(hub_cache: Path) -> None:
    """Point SDK cache lookups at bundled assets and prohibit remote fallback."""

    resolved = str(hub_cache.expanduser().resolve())
    os.environ["HF_HUB_CACHE"] = resolved
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
