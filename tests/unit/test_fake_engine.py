"""Tests for the offline fake TTS adapter."""

import numpy as np
import pytest

from vntts.db.models import EngineSynthesisOptions
from vntts.engines.fake_engine import FakeTTSEngine
from vntts.utils.exceptions import EngineNotLoadedError, ValidationError


def test_load_and_unload_state() -> None:
    engine = FakeTTSEngine(processing_delay=0)
    assert not engine.is_loaded()

    engine.load("cpu")
    assert engine.is_loaded()

    engine.unload()
    assert not engine.is_loaded()


def test_synthesis_requires_loaded_engine() -> None:
    engine = FakeTTSEngine(processing_delay=0)

    with pytest.raises(EngineNotLoadedError):
        engine.synthesize("Xin chào", EngineSynthesisOptions("female-south"))


def test_voice_list_contains_three_valid_voices() -> None:
    voices = FakeTTSEngine(processing_delay=0).list_voices()

    assert len(voices) >= 3
    assert len({voice.voice_id for voice in voices}) == len(voices)


def test_invalid_voice_is_rejected() -> None:
    engine = FakeTTSEngine(processing_delay=0)
    engine.load("cpu")

    with pytest.raises(ValidationError, match="không tồn tại"):
        engine.synthesize("Xin chào", EngineSynthesisOptions("missing"))


def test_synthesis_returns_valid_numpy_audio() -> None:
    engine = FakeTTSEngine(processing_delay=0)
    engine.load("auto")

    result = engine.synthesize("Xin chào Việt Nam", EngineSynthesisOptions("female-north"))

    assert isinstance(result.audio, np.ndarray)
    assert result.audio.ndim == 1
    assert result.audio.dtype == np.float32
    assert result.audio.size > 0
    assert result.sample_rate > 0
