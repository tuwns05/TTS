"""Tests for waveform retention and in-memory playback lifecycle."""

from __future__ import annotations

import io
import wave

import numpy as np
import pytest

from vntts.db.models import SynthesisResult
from vntts.services.playback import PlaybackService
from vntts.utils.exceptions import PlaybackError


def _result(value: float = 0.25) -> SynthesisResult:
    return SynthesisResult(np.full(4_800, value, dtype=np.float32), 48_000)


def test_set_audio_retains_waveform_and_writes_pcm_wav(qapp) -> None:  # type: ignore[no-untyped-def]
    service = PlaybackService()
    result = _result()

    service.set_audio(result)

    wav_bytes = service.current_wav_bytes
    assert service.current_result is result
    assert service.has_audio
    assert service.state == PlaybackService.READY
    assert wav_bytes is not None
    with wave.open(io.BytesIO(wav_bytes), "rb") as source:
        assert source.getnchannels() == 1
        assert source.getsampwidth() == 2
        assert source.getframerate() == 48_000
        assert source.getnframes() == result.audio.size

    service.shutdown()
    assert service.current_result is None
    assert service.current_wav_bytes is None


def test_replacing_audio_releases_previous_buffer(qapp) -> None:  # type: ignore[no-untyped-def]
    service = PlaybackService()
    service.set_audio(_result(0.1))
    first_buffer = service._buffer

    service.set_audio(_result(0.2))

    assert first_buffer is not None and not first_buffer.isOpen()
    assert service._buffer is not None and service._buffer is not first_buffer
    service.shutdown()


def test_play_pause_and_stop_update_service_state(qapp) -> None:  # type: ignore[no-untyped-def]
    service = PlaybackService()
    service.set_audio(_result())
    assert service._audio_sink is None

    service.play()
    assert service._audio_sink is not None
    assert service.state == PlaybackService.PLAYING
    service.pause()
    assert service.state == PlaybackService.PAUSED
    service.stop()
    assert service.state == PlaybackService.STOPPED
    assert service.has_audio
    service.shutdown()


def test_invalid_waveform_is_rejected_and_not_retained(qapp) -> None:  # type: ignore[no-untyped-def]
    service = PlaybackService()
    invalid = SynthesisResult(np.array([0.0, np.nan], dtype=np.float32), 48_000)

    with pytest.raises(PlaybackError, match="Waveform không hợp lệ"):
        service.set_audio(invalid)

    assert not service.has_audio
    assert service.current_wav_bytes is None


def test_export_audio_writes_wav_and_mp3(qapp, tmp_path) -> None:  # type: ignore[no-untyped-def]
    service = PlaybackService()
    service.set_audio(_result())

    wav_path = service.export_audio(tmp_path / "speech", "wav")
    mp3_path = service.export_audio(tmp_path / "speech", "mp3")

    assert wav_path.suffix == ".wav"
    assert wav_path.read_bytes().startswith(b"RIFF")
    assert mp3_path.suffix == ".mp3"
    assert len(mp3_path.read_bytes()) > 0
    service.shutdown()


def test_invalidated_audio_device_stops_and_reports_only_once(qapp) -> None:  # type: ignore[no-untyped-def]
    service = PlaybackService()
    service.set_audio(_result())
    messages: list[str] = []
    service.error_occurred.connect(messages.append)
    service.play()
    service._sink_device_id = b"removed-device"

    service._on_audio_outputs_changed()
    service._on_audio_outputs_changed()

    assert service.state == PlaybackService.STOPPED
    assert messages == [PlaybackService.AUDIO_DEVICE_ERROR]
    assert service._audio_sink is None
    service.shutdown()


def test_unchanged_audio_device_notification_does_not_stop_playback(qapp) -> None:  # type: ignore[no-untyped-def]
    service = PlaybackService()
    service.set_audio(_result())
    messages: list[str] = []
    service.error_occurred.connect(messages.append)
    service.play()
    active_sink = service._audio_sink

    service._on_audio_outputs_changed()

    assert service.state == PlaybackService.PLAYING
    assert service._audio_sink is active_sink
    assert messages == []
    service.shutdown()


def test_loading_audio_does_not_open_the_windows_audio_device(qapp) -> None:  # type: ignore[no-untyped-def]
    service = PlaybackService()
    service.set_audio(_result())
    messages: list[str] = []
    service.error_occurred.connect(messages.append)

    assert messages == []
    assert service.state == PlaybackService.READY
    assert service.has_audio
    assert service._audio_sink is None
    service.shutdown()
