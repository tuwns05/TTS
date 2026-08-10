"""Local waveform playback backed by Qt Multimedia."""

from __future__ import annotations

import importlib
import io
from pathlib import Path
import wave

import numpy as np
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from vntts.db.models import SynthesisResult
from vntts.utils.exceptions import PlaybackError


class PlaybackService(QObject):
    """Own the current waveform, temporary WAV and Qt playback objects."""

    state_changed = Signal(str)
    position_changed = Signal(int)
    error_occurred = Signal(str)

    EMPTY = "empty"
    READY = "ready"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._current_result: SynthesisResult | None = None
        self._wav_data: QByteArray | None = None
        self._buffer: QBuffer | None = None
        self._state = self.EMPTY

        self._audio_output = QAudioOutput(self)
        self._audio_output.setVolume(1.0)
        self._player = QMediaPlayer(self)
        self._player.setAudioOutput(self._audio_output)
        self._player.positionChanged.connect(
            lambda position: self.position_changed.emit(int(position))
        )
        self._player.playbackStateChanged.connect(self._on_player_state_changed)
        self._player.mediaStatusChanged.connect(self._on_media_status_changed)
        self._player.errorOccurred.connect(self._on_player_error)

    @property
    def state(self) -> str:
        """Return the current UI-friendly playback state."""

        return self._state

    @property
    def has_audio(self) -> bool:
        """Return whether a synthesized waveform is ready for playback."""

        return self._current_result is not None and self._buffer is not None

    @property
    def current_result(self) -> SynthesisResult | None:
        """Return the waveform retained for the current playback session."""

        return self._current_result

    @property
    def current_wav_bytes(self) -> bytes | None:
        """Return the in-memory PCM WAV retained by Qt Multimedia."""

        return bytes(self._wav_data) if self._wav_data is not None else None

    def set_audio(self, result: SynthesisResult) -> None:
        """Replace the current waveform and prepare an in-memory PCM WAV."""

        self.clear()
        wav_data = QByteArray(self._encode_wav(result))
        buffer = QBuffer(self)
        buffer.setData(wav_data)
        if not buffer.open(QIODevice.OpenModeFlag.ReadOnly):
            buffer.deleteLater()
            raise PlaybackError("Không thể mở bộ đệm âm thanh để phát.")
        self._current_result = result
        self._wav_data = wav_data
        self._buffer = buffer
        self._player.setSourceDevice(buffer, QUrl("memory:current-audio.wav"))
        self._set_state(self.READY)

    def export_audio(self, destination: str | Path, audio_format: str) -> Path:
        """Write the current synthesized clip as WAV or MP3."""

        if self._current_result is None or self._wav_data is None:
            raise PlaybackError("Chưa có audio để xuất.")
        normalized_format = audio_format.lower()
        if normalized_format not in {"wav", "mp3"}:
            raise PlaybackError(f"Định dạng audio không được hỗ trợ: {audio_format}")

        output_path = Path(destination)
        if output_path.suffix.lower() != f".{normalized_format}":
            output_path = output_path.with_suffix(f".{normalized_format}")
        try:
            data = (
                bytes(self._wav_data)
                if normalized_format == "wav"
                else self._encode_mp3(self._current_result)
            )
            output_path.write_bytes(data)
        except PlaybackError:
            raise
        except OSError as exc:
            raise PlaybackError(f"Không thể lưu file audio: {exc}") from exc
        return output_path

    def play(self) -> None:
        """Start or resume the current audio."""

        if not self.has_audio:
            raise PlaybackError("Chưa có audio để phát.")
        if self._player.duration() > 0 and self._player.position() >= self._player.duration():
            self._player.setPosition(0)
        self._player.play()
        self._set_state(self.PLAYING)

    def pause(self) -> None:
        """Pause playback while retaining the current position."""

        if self._state != self.PLAYING:
            return
        self._player.pause()
        self._set_state(self.PAUSED)

    def stop(self) -> None:
        """Stop playback while keeping the waveform available for replay."""

        if not self.has_audio:
            return
        self._player.stop()
        self._set_state(self.STOPPED)

    def seek(self, position_ms: int) -> None:
        """Seek within the current in-memory clip."""

        if not self.has_audio:
            return
        duration = self._player.duration()
        upper_bound = duration if duration > 0 else max(0, int(position_ms))
        self._player.setPosition(max(0, min(int(position_ms), upper_bound)))

    def clear(self) -> None:
        """Release the current waveform, media source and memory buffer."""

        self._player.stop()
        self._player.setSource(QUrl())
        buffer, self._buffer = self._buffer, None
        self._current_result = None
        self._wav_data = None
        if buffer is not None:
            buffer.close()
            buffer.deleteLater()
        self._set_state(self.EMPTY)

    def shutdown(self) -> None:
        """Release all playback resources before application shutdown."""

        self.clear()

    @staticmethod
    def _encode_wav(result: SynthesisResult) -> bytes:
        audio = np.asarray(result.audio, dtype=np.float32)
        if audio.ndim != 1 or audio.size == 0 or not bool(np.isfinite(audio).all()):
            raise PlaybackError("Waveform không hợp lệ để phát.")
        pcm = np.rint(np.clip(audio, -1.0, 1.0) * 32_767).astype("<i2")
        destination = io.BytesIO()
        with wave.open(destination, "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(result.sample_rate)
            output.writeframes(pcm.tobytes())
        return destination.getvalue()

    @staticmethod
    def _encode_mp3(result: SynthesisResult) -> bytes:
        try:
            lameenc = importlib.import_module("lameenc")
        except ImportError as exc:
            raise PlaybackError(
                "Thiếu bộ mã hóa MP3. Hãy cài dependency 'lameenc'."
            ) from exc

        audio = np.asarray(result.audio, dtype=np.float32)
        if audio.ndim != 1 or audio.size == 0 or not bool(np.isfinite(audio).all()):
            raise PlaybackError("Waveform không hợp lệ để xuất.")
        pcm = np.rint(np.clip(audio, -1.0, 1.0) * 32_767).astype("<i2")
        try:
            encoder = lameenc.Encoder()
            encoder.set_bit_rate(192)
            encoder.set_in_sample_rate(result.sample_rate)
            encoder.set_channels(1)
            encoder.set_quality(2)
            return encoder.encode(pcm.tobytes()) + encoder.flush()
        except Exception as exc:
            raise PlaybackError(f"Không thể mã hóa MP3: {exc}") from exc

    def _on_player_state_changed(
        self,
        state: QMediaPlayer.PlaybackState,
    ) -> None:
        mapping = {
            QMediaPlayer.PlaybackState.PlayingState: self.PLAYING,
            QMediaPlayer.PlaybackState.PausedState: self.PAUSED,
            QMediaPlayer.PlaybackState.StoppedState: self.STOPPED,
        }
        if self.has_audio:
            self._set_state(mapping[state])

    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia and self.has_audio:
            self._set_state(self.STOPPED)

    def _on_player_error(
        self,
        _error: QMediaPlayer.Error,
        message: str,
    ) -> None:
        if not message:
            message = "Thiết bị phát âm thanh không khả dụng."
        self._set_state(self.STOPPED if self.has_audio else self.EMPTY)
        self.error_occurred.emit(message)

    def _set_state(self, state: str) -> None:
        if self._state == state:
            return
        self._state = state
        self.state_changed.emit(state)
