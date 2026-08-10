"""Persistent local reference-audio profiles for VieNeu v3 voice cloning."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import uuid4

import soundfile as sf

from vntts.services.audio_processor import preprocess_reference_audio
from vntts.utils.exceptions import ValidationError


@dataclass(frozen=True)
class VoiceProfile:
    """A reusable voice-cloning reference owned by the local user."""

    profile_id: str
    name: str
    reference_audio_path: str
    status: str = "ready"
    warnings: tuple[str, ...] = ()


class VoiceProfileStore:
    """Preprocess reference audio and persist reusable local profiles."""

    SUPPORTED_SUFFIXES = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}

    def __init__(self, data_dir: Path) -> None:
        self._root = data_dir / "voice_profiles"
        self._audio_dir = self._root / "audio"
        self._index_path = self._root / "profiles.json"
        self._audio_dir.mkdir(parents=True, exist_ok=True)

    def list_profiles(self) -> list[VoiceProfile]:
        if not self._index_path.is_file():
            return []
        try:
            payload = json.loads(self._index_path.read_text(encoding="utf-8"))
            return [
                VoiceProfile(
                    profile_id=item["profile_id"],
                    name=item["name"],
                    reference_audio_path=item["reference_audio_path"],
                    status=item.get("status", "ready"),
                    warnings=tuple(item.get("warnings", ())),
                )
                for item in payload
            ]
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise ValidationError("Không thể đọc danh sách hồ sơ giọng.") from exc

    def create(self, name: str, source_audio: str | Path) -> VoiceProfile:
        normalized_name = self._validate_name(name)
        source = Path(source_audio).expanduser().resolve()
        if not source.is_file():
            raise ValidationError("Không tìm thấy file âm thanh mẫu.")
        if source.suffix.lower() not in self.SUPPORTED_SUFFIXES:
            raise ValidationError("File mẫu phải là WAV, MP3, FLAC, M4A hoặc OGG.")

        processed = preprocess_reference_audio(source)
        profile_id = uuid4().hex
        destination = self._audio_dir / f"{profile_id}.wav"
        try:
            sf.write(
                destination,
                processed.audio,
                processed.sample_rate,
                format="WAV",
                subtype="PCM_16",
            )
        except (OSError, RuntimeError, ValueError, sf.SoundFileError) as exc:
            raise ValidationError("Không thể lưu file âm thanh mẫu.") from exc
        profile = VoiceProfile(
            profile_id,
            normalized_name,
            str(destination.resolve()),
            warnings=processed.warnings,
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
                    profile.reference_audio_path,
                    profile.status,
                    profile.warnings,
                )
                profiles[index] = updated
                self._save(profiles)
                return updated
        raise ValidationError("Không tìm thấy hồ sơ giọng cần sửa.")

    def delete(self, profile_id: str) -> None:
        profiles = self.list_profiles()
        selected = next((item for item in profiles if item.profile_id == profile_id), None)
        if selected is None:
            raise ValidationError("Không tìm thấy hồ sơ giọng cần xóa.")
        self._save([item for item in profiles if item.profile_id != profile_id])
        try:
            Path(selected.reference_audio_path).unlink(missing_ok=True)
        except OSError as exc:
            raise ValidationError("Đã xóa hồ sơ nhưng không thể xóa file âm thanh mẫu.") from exc

    def _save(self, profiles: list[VoiceProfile]) -> None:
        temporary = self._index_path.with_suffix(".tmp")
        try:
            temporary.write_text(
                json.dumps([asdict(item) for item in profiles], ensure_ascii=False, indent=2),
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
