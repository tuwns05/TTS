"""One-time VieNeu enrollment for reusable cloned voices."""

from __future__ import annotations

import tempfile
from pathlib import Path

import soundfile as sf

from vntts.db.models import VIENEU_V3_ENGINE_ID
from vntts.services.audio_processor import preprocess_reference_audio
from vntts.services.synthesis import SynthesizeSpeech
from vntts.services.voice_profiles import VoiceProfile, VoiceProfileStore
from vntts.utils.exceptions import AppError, ValidationError


class VoiceEnrollmentService:
    """Preflight audio, extract VieNeu features once, then discard the audio."""

    def __init__(
        self,
        synthesize_speech: SynthesizeSpeech,
        store: VoiceProfileStore,
    ) -> None:
        self._synthesize_speech = synthesize_speech
        self._store = store

    def enroll(self, name: str, source_audio: str | Path) -> VoiceProfile:
        """Create a feature-only profile from an uploaded or recorded sample."""

        source = Path(source_audio).expanduser().resolve()
        if not source.is_file():
            raise ValidationError("Không tìm thấy file âm thanh mẫu.")

        processed = preprocess_reference_audio(source)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix="vntts-enroll-",
                suffix=".wav",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
            sf.write(
                temporary_path,
                processed.audio,
                processed.sample_rate,
                format="WAV",
                subtype="PCM_16",
            )
            speaker_emb, ref_codes = self._synthesize_speech.encode_voice_reference(
                VIENEU_V3_ENGINE_ID,
                str(temporary_path),
            )
            return self._store.create(
                name,
                speaker_emb,
                ref_codes,
                processed.warnings,
            )
        except AppError:
            raise
        except (OSError, RuntimeError, ValueError, sf.SoundFileError) as exc:
            raise ValidationError(
                "Không thể chuẩn bị mẫu giọng để VieNeu xử lý."
            ) from exc
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass
