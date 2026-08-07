"""Local waveform playback backed by Qt Multimedia."""

from __future__ import annotations

import io
import wave

import numpy as np
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from vntts.db.models import SynthesisResult
from vntts.utils.exceptions import PlaybackError


class PlaybackService(QObject):
    """Own the current waveform, temporary WAV and Qt playback objects."""

    state_changed = Signal(str)
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
