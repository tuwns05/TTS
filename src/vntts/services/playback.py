"""Local waveform playback backed by Qt Multimedia."""

from __future__ import annotations

import importlib
import io
import wave
from pathlib import Path

import numpy as np
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QObject, QTimer, Signal
from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices, QtAudio

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

    AUDIO_DEVICE_ERROR = (
        "Thiết bị phát âm thanh đã thay đổi hoặc không còn khả dụng. "
        "Hãy kiểm tra đầu ra âm thanh trong Windows rồi nhấn Phát lại."
    )

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._current_result: SynthesisResult | None = None
        self._wav_data: QByteArray | None = None
        self._pcm_data: QByteArray | None = None
        self._buffer: QBuffer | None = None
        self._state = self.EMPTY
        self._audio_error_reported = False
        self._playback_requested = False
        self._position_ms = 0
        self._duration_ms = 0
        self._sink_start_position_ms = 0

        self._media_devices = QMediaDevices(self)
        self._media_devices.audioOutputsChanged.connect(self._on_audio_outputs_changed)
        self._audio_sink: QAudioSink | None = None
        self._sink_device_id: bytes | None = None
        self._position_timer = QTimer(self)
        self._position_timer.setInterval(50)
        self._position_timer.timeout.connect(self._update_position)

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
        pcm_data = QByteArray(self._encode_pcm(result))
        wav_data = QByteArray(self._encode_wav(result))
        buffer = QBuffer(self)
        buffer.setData(pcm_data)
        if not buffer.open(QIODevice.OpenModeFlag.ReadOnly):
            buffer.deleteLater()
            raise PlaybackError("Không thể mở bộ đệm âm thanh để phát.")
        self._current_result = result
        self._wav_data = wav_data
        self._pcm_data = pcm_data
        self._buffer = buffer
        self._audio_error_reported = False
        self._position_ms = 0
        self._duration_ms = round(result.audio.size / result.sample_rate * 1_000)
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
        self._playback_requested = True
        self._audio_error_reported = False
        if self._state == self.PAUSED and self._audio_sink is not None:
            self._audio_sink.resume()
            self._position_timer.start()
        else:
            if self._position_ms >= self._duration_ms:
                self._set_position(0)
            try:
                self._start_audio_sink()
            except PlaybackError:
                self._playback_requested = False
                raise
        self._set_state(self.PLAYING)

    def pause(self) -> None:
        """Pause playback while retaining the current position."""

        if self._state != self.PLAYING:
            return
        if self._audio_sink is not None:
            self._audio_sink.suspend()
        self._position_timer.stop()
        self._update_position()
        self._set_state(self.PAUSED)

    def stop(self) -> None:
        """Stop playback while keeping the waveform available for replay."""

        if not self.has_audio:
            return
        self._playback_requested = False
        self._release_audio_sink()
        self._set_position(0)
        self._set_state(self.STOPPED)

    def seek(self, position_ms: int) -> None:
        """Seek within the current in-memory clip."""

        if not self.has_audio:
            return
        target = max(0, min(int(position_ms), self._duration_ms))
        was_playing = self._state == self.PLAYING
        was_paused = self._state == self.PAUSED
        if self._audio_sink is not None:
            self._release_audio_sink()
        self._set_position(target)
        if was_playing or was_paused:
            self._start_audio_sink()
            if was_paused and self._audio_sink is not None:
                self._audio_sink.suspend()
                self._position_timer.stop()

    def clear(self) -> None:
        """Release the current waveform, media source and memory buffer."""

        self._release_audio_sink()
        buffer, self._buffer = self._buffer, None
        self._current_result = None
        self._wav_data = None
        self._pcm_data = None
        self._audio_error_reported = False
        self._playback_requested = False
        self._position_ms = 0
        self._duration_ms = 0
        if buffer is not None:
            buffer.close()
            buffer.deleteLater()
        self._set_state(self.EMPTY)

    def shutdown(self) -> None:
        """Release all playback resources before application shutdown."""

        self.clear()

    @staticmethod
    def _encode_pcm(result: SynthesisResult) -> bytes:
        audio = np.asarray(result.audio, dtype=np.float32)
        if audio.ndim != 1 or audio.size == 0 or not bool(np.isfinite(audio).all()):
            raise PlaybackError(
                "Waveform kh\u00f4ng h\u1ee3p l\u1ec7 \u0111\u1ec3 ph\u00e1t."
            )
        return np.rint(np.clip(audio, -1.0, 1.0) * 32_767).astype("<i2").tobytes()

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

    def _start_audio_sink(self) -> None:
        if self._current_result is None or self._buffer is None:
            raise PlaybackError("Chưa có audio để phát.")
        device = QMediaDevices.defaultAudioOutput()
        if device.isNull():
            raise PlaybackError("Không tìm thấy thiết bị phát âm thanh trong Windows.")

        audio_format = QAudioFormat()
        audio_format.setSampleRate(self._current_result.sample_rate)
        audio_format.setChannelCount(1)
        audio_format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if not device.isFormatSupported(audio_format):
            raise PlaybackError(
                "Thiết bị âm thanh hiện tại không hỗ trợ định dạng PCM của bản nghe thử."
            )

        self._release_audio_sink()
        self._seek_buffer(self._position_ms)
        sink = QAudioSink(device, audio_format, self)
        self._audio_sink = sink
        self._sink_device_id = bytes(device.id())
        self._sink_start_position_ms = self._position_ms
        sink.start(self._buffer)
        if sink.error() not in {QtAudio.Error.NoError, QtAudio.Error.UnderrunError}:
            self._playback_requested = False
            self._release_audio_sink()
            self._set_state(self.STOPPED)
            raise PlaybackError(self.AUDIO_DEVICE_ERROR)
        self._position_timer.start()

    def _release_audio_sink(self) -> None:
        self._position_timer.stop()
        sink, self._audio_sink = self._audio_sink, None
        self._sink_device_id = None
        if sink is not None:
            sink.stop()
            sink.deleteLater()

    def _seek_buffer(self, position_ms: int) -> None:
        if self._buffer is None or self._current_result is None:
            return
        bytes_per_second = self._current_result.sample_rate * 2
        byte_offset = position_ms * bytes_per_second // 1_000
        byte_offset -= byte_offset % 2
        self._buffer.seek(min(byte_offset, self._buffer.size()))

    def _update_position(self) -> None:
        sink = self._audio_sink
        if sink is None:
            return
        state = sink.state()
        if state == QtAudio.State.IdleState:
            self._finish_playback()
            return
        if (
            state == QtAudio.State.StoppedState
            and sink.error() != QtAudio.Error.NoError
        ):
            self._handle_audio_sink_error()
            return
        elapsed_ms = max(0, sink.processedUSecs() // 1_000)
        self._set_position(self._sink_start_position_ms + elapsed_ms)

    def _set_position(self, position_ms: int) -> None:
        position = max(0, min(int(position_ms), self._duration_ms))
        if position == self._position_ms:
            return
        self._position_ms = position
        self.position_changed.emit(position)

    def _finish_playback(self) -> None:
        self._set_position(self._duration_ms)
        self._playback_requested = False
        self._release_audio_sink()
        self._set_state(self.STOPPED)

    def _handle_audio_sink_error(self) -> None:
        if self._audio_error_reported:
            return
        self._audio_error_reported = True
        self._playback_requested = False
        self._release_audio_sink()
        self._set_state(self.STOPPED if self.has_audio else self.EMPTY)
        self.error_occurred.emit(self.AUDIO_DEVICE_ERROR)

    def _on_audio_outputs_changed(self) -> None:
        if self._audio_sink is None and not self._playback_requested:
            return
        available_device_ids = {
            bytes(device.id()) for device in QMediaDevices.audioOutputs()
        }
        if self._sink_device_id in available_device_ids:
            return
        self._playback_requested = False
        self._release_audio_sink()
        self._set_state(self.STOPPED)
        if not self._audio_error_reported:
            self._audio_error_reported = True
            self.error_occurred.emit(self.AUDIO_DEVICE_ERROR)

    def _set_state(self, state: str) -> None:
        if self._state == state:
            return
        self._state = state
        self.state_changed.emit(state)
