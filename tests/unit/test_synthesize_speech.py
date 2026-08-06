"""Tests for the synthesize-speech use case."""

import pytest
from loguru import logger

from vntts.application.services.engine_factory import EngineFactory
from vntts.application.services.engine_registry import EngineRegistry
from vntts.application.use_cases.synthesize_speech import SynthesizeSpeech
from vntts.domain.exceptions import EngineNotFoundError, ValidationError
from vntts.domain.tts.models import AudioEffects, EngineSynthesisOptions, SynthesisRequest
from vntts.infrastructure.engines.fake_engine import FakeTTSEngine


def _use_case(max_length: int = 100) -> SynthesizeSpeech:
    registry = EngineRegistry()
    registry.register(
        "fake",
        lambda: FakeTTSEngine(processing_delay=0),
        FakeTTSEngine.INFO,
    )
    return SynthesizeSpeech(EngineFactory(registry), registry, max_length)


def _request(text: str, engine_id: str = "fake") -> SynthesisRequest:
    return SynthesisRequest(
        text=text,
        engine_id=engine_id,
        options=EngineSynthesisOptions("female-south"),
        effects=AudioEffects(),
    )


def test_rejects_blank_text() -> None:
    with pytest.raises(ValidationError, match="không được để trống"):
        _use_case().execute(_request("   "))


def test_rejects_text_above_configured_limit() -> None:
    with pytest.raises(ValidationError, match="giới hạn"):
        _use_case(max_length=3).execute(_request("abcd"))


def test_rejects_unknown_engine() -> None:
    with pytest.raises(EngineNotFoundError):
        _use_case().execute(_request("Xin chào", "missing"))


def test_loads_engine_and_returns_valid_result() -> None:
    result = _use_case().execute(_request("Xin chào"))

    assert result.audio.ndim == 1
    assert result.sample_rate > 0


def test_does_not_log_full_user_text() -> None:
    sensitive_text = "NỘI DUNG RIÊNG TƯ KHÔNG ĐƯỢC GHI LOG"
    messages: list[str] = []
    sink_id = logger.add(lambda message: messages.append(str(message)))
    try:
        _use_case().execute(_request(sensitive_text))
    finally:
        logger.remove(sink_id)

    assert all(sensitive_text not in message for message in messages)

