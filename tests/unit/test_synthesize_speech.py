"""Tests for the synthesize-speech use case."""

import numpy as np

import pytest
from loguru import logger

from vntts.db.models import AudioEffects, EngineSynthesisOptions, SynthesisRequest
from vntts.engines.base import EngineCapabilities
from vntts.engines.factory import EngineFactory, EngineRegistry
from vntts.services.synthesis import SynthesizeSpeech
from vntts.utils.exceptions import EngineNotFoundError, ValidationError
from tests.stubs import StubTTSEngine


def _use_case() -> SynthesizeSpeech:
    registry = EngineRegistry()
    registry.register(
        "stub",
        StubTTSEngine,
        StubTTSEngine.INFO,
    )
    return SynthesizeSpeech(EngineFactory(registry), registry)


def _request(
    text: str,
    engine_id: str = "stub",
    effects: AudioEffects | None = None,
) -> SynthesisRequest:
    return SynthesisRequest(
        text=text,
        engine_id=engine_id,
        options=EngineSynthesisOptions("female-south"),
        effects=effects or AudioEffects(),
    )


def test_rejects_blank_text() -> None:
    with pytest.raises(ValidationError, match="không được để trống"):
        _use_case().execute(_request("   "))


def test_accepts_text_above_previous_ten_thousand_character_limit() -> None:
    result = _use_case().execute(_request("a" * 10_001))

    assert result.audio.size > 0


def test_rejects_unknown_engine() -> None:
    with pytest.raises(EngineNotFoundError):
        _use_case().execute(_request("Xin chào", "missing"))


def test_rejects_style_not_supported_by_engine() -> None:
    request = SynthesisRequest(
        text="Xin chào",
        engine_id="stub",
        options=EngineSynthesisOptions("female-south", style_id="quang_cao"),
        effects=AudioEffects(),
    )

    with pytest.raises(ValidationError, match="Phong cách đọc"):
        _use_case().execute(request)


def test_loads_engine_and_returns_valid_result() -> None:
    result = _use_case().execute(_request("Xin chào"))

    assert result.audio.ndim == 1
    assert result.sample_rate > 0


def test_clone_request_bypasses_preset_validation(tmp_path) -> None:
    class CloneCapableStub(StubTTSEngine):
        CAPABILITIES = EngineCapabilities(
            voice_cloning=True,
            native_speed_control=False,
            native_pitch_control=False,
            streaming=False,
            cpu_supported=True,
            gpu_supported=False,
        )
        received_options: EngineSynthesisOptions | None = None

        def synthesize(self, text, options):  # type: ignore[no-untyped-def]
            CloneCapableStub.received_options = options
            preset_options = EngineSynthesisOptions("female-south")
            return super().synthesize(text, preset_options)

    registry = EngineRegistry()
    registry.register(
        "stub",
        CloneCapableStub,
        CloneCapableStub.INFO,
        CloneCapableStub.CAPABILITIES,
    )
    reference = tmp_path / "voice.wav"
    reference.write_bytes(b"RIFF-sample")
    request = SynthesisRequest(
        text="Xin chào",
        engine_id="stub",
        options=EngineSynthesisOptions("clone:profile", str(reference)),
        effects=AudioEffects(),
    )

    result = SynthesizeSpeech(EngineFactory(registry), registry).execute(request)

    assert result.audio.size > 0
    assert CloneCapableStub.received_options == request.options


def test_speed_control_changes_duration_without_changing_sample_rate() -> None:
    result = _use_case().execute(
        _request("Xin chào", effects=AudioEffects(speed=2.0))
    )

    assert result.sample_rate == 24_000
    assert result.audio.size == 3_000


def test_pitch_control_shifts_frequency_without_changing_duration() -> None:
    result = _use_case().execute(
        _request("Xin chào", effects=AudioEffects(pitch_semitones=12.0))
    )
    frequencies = np.fft.rfftfreq(result.audio.size, d=1 / result.sample_rate)
    peak_frequency = frequencies[np.argmax(np.abs(np.fft.rfft(result.audio)))]

    assert result.audio.size == 6_000
    assert peak_frequency == pytest.approx(360.0, abs=8.0)


def test_volume_control_applies_decibel_gain() -> None:
    neutral = _use_case().execute(_request("Xin chào"))
    quieter = _use_case().execute(
        _request("Xin chào", effects=AudioEffects(volume_db=-6.0))
    )
    neutral_rms = float(np.sqrt(np.mean(np.square(neutral.audio))))
    quieter_rms = float(np.sqrt(np.mean(np.square(quieter.audio))))

    assert quieter_rms / neutral_rms == pytest.approx(10 ** (-6 / 20), rel=1e-4)


def test_does_not_log_full_user_text() -> None:
    sensitive_text = "NỘI DUNG RIÊNG TƯ KHÔNG ĐƯỢC GHI LOG"
    messages: list[str] = []
    sink_id = logger.add(lambda message: messages.append(str(message)))
    try:
        _use_case().execute(_request(sensitive_text))
    finally:
        logger.remove(sink_id)

    assert all(sensitive_text not in message for message in messages)
