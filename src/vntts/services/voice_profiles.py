"""Persistent numerical voice profiles for VieNeu v3 voice cloning."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import uuid4

import numpy as np

from vntts.utils.exceptions import ValidationError


@dataclass(frozen=True)
class VoiceProfile:
    """Reusable VieNeu voice features owned by the local user."""

    profile_id: str
    name: str
    voice_artifact_path: str
    status: str = "ready"
    warnings: tuple[str, ...] = ()


class VoiceProfileStore:
    """Persist reusable VieNeu speaker embeddings and reference codes."""

    def __init__(self, data_dir: Path) -> None:
        self._root = data_dir / "voice_profiles"
        self._artifact_dir = self._root / "artifacts"
        self._index_path = self._root / "profiles.json"
        self._artifact_dir.mkdir(parents=True, exist_ok=True)

    def list_profiles(self) -> list[VoiceProfile]:
        if not self._index_path.is_file():
            return []
        try:
            payload = json.loads(self._index_path.read_text(encoding="utf-8"))
            return [
                VoiceProfile(
                    profile_id=item["profile_id"],
                    name=item["name"],
                    voice_artifact_path=item["voice_artifact_path"],
                    status=item.get("status", "ready"),
                    warnings=tuple(item.get("warnings", ())),
                )
                for item in payload
                if "voice_artifact_path" in item
            ]
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise ValidationError("Không thể đọc danh sách hồ sơ giọng.") from exc

    def create(
        self,
        name: str,
        speaker_emb: np.ndarray,
        ref_codes: np.ndarray,
        warnings: tuple[str, ...] = (),
    ) -> VoiceProfile:
        normalized_name = self._validate_name(name)
        speaker = np.asarray(speaker_emb, dtype=np.float32).reshape(-1)
        codes = np.asarray(ref_codes, dtype=np.int64)
        if speaker.size == 0 or codes.size == 0:
            raise ValidationError("Đặc điểm giọng do VieNeu tạo ra không hợp lệ.")
        if not bool(np.isfinite(speaker).all()):
            raise ValidationError("Embedding giọng chứa dữ liệu không hợp lệ.")
        profile_id = uuid4().hex
        destination = self._artifact_dir / f"{profile_id}.npz"
        try:
            np.savez_compressed(
                destination,
                speaker_emb=speaker,
                ref_codes=codes,
            )
        except (OSError, ValueError) as exc:
            raise ValidationError("Không thể lưu đặc điểm giọng.") from exc
        profile = VoiceProfile(
            profile_id,
            normalized_name,
            str(destination.resolve()),
            warnings=tuple(warnings),
        )
        profiles = self.list_profiles()
        profiles.append(profile)
        try:
            self._save(profiles)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        return profile

    def rename(self, profile_id: str, name: str) -> VoiceProfile:
        normalized_name = self._validate_name(name)
        profiles = self.list_profiles()
        for index, profile in enumerate(profiles):
            if profile.profile_id == profile_id:
                updated = VoiceProfile(
                    profile.profile_id,
                    normalized_name,
                    profile.voice_artifact_path,
                    profile.status,
                    profile.warnings,
                )
                profiles[index] = updated
                self._save(profiles)
                return updated
        raise ValidationError("Không tìm thấy hồ sơ giọng cần sửa.")

    def delete(self, profile_id: str) -> None:
        profiles = self.list_profiles()
        selected = next(
            (item for item in profiles if item.profile_id == profile_id), None
        )
        if selected is None:
            raise ValidationError("Không tìm thấy hồ sơ giọng cần xóa.")
        self._save([item for item in profiles if item.profile_id != profile_id])
        try:
            Path(selected.voice_artifact_path).unlink(missing_ok=True)
        except OSError as exc:
            raise ValidationError(
                "Đã xóa hồ sơ nhưng không thể xóa đặc điểm giọng."
            ) from exc

    def _save(self, profiles: list[VoiceProfile]) -> None:
        temporary = self._index_path.with_suffix(".tmp")
        try:
            temporary.write_text(
                json.dumps(
                    [asdict(item) for item in profiles], ensure_ascii=False, indent=2
                ),
                encoding="utf-8",
            )
            temporary.replace(self._index_path)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise ValidationError("Không thể lưu danh sách hồ sơ giọng.") from exc

    @staticmethod
    def _validate_name(name: str) -> str:
        normalized = name.strip()
        if not normalized:
            raise ValidationError("Vui lòng đặt tên cho hồ sơ giọng.")
        if len(normalized) > 80:
            raise ValidationError("Tên hồ sơ giọng không được vượt quá 80 ký tự.")
        return normalized
