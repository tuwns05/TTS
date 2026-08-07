"""Tests for the synthesize-speech use case."""

import pytest
from loguru import logger

from vntts.db.models import AudioEffects, EngineSynthesisOptions, SynthesisRequest
from vntts.engines.factory import EngineFactory, EngineRegistry
from vntts.services.synthesis import SynthesizeSpeech
from vntts.utils.exceptions import EngineNotFoundError, ValidationError
from tests.stubs import StubTTSEngine


def _use_case(max_length: int = 100) -> SynthesizeSpeech:
    registry = EngineRegistry()
    registry.register(
        "stub",
        StubTTSEngine,
        StubTTSEngine.INFO,
    )
    return SynthesizeSpeech(EngineFactory(registry), registry, max_length)


def _request(text: str, engine_id: str = "stub") -> SynthesisRequest:
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
