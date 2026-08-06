"""Tests for lazy engine registration."""

import pytest

from vntts.application.services.engine_registry import EngineRegistry
from vntts.domain.exceptions import EngineNotFoundError, ValidationError
from vntts.infrastructure.engines.fake_engine import FakeTTSEngine


def test_register_and_create_engine() -> None:
    registry = EngineRegistry()
    registry.register("fake", FakeTTSEngine, FakeTTSEngine.INFO)

    assert registry.contains("fake")
    assert isinstance(registry.create("fake"), FakeTTSEngine)


def test_duplicate_engine_id_is_rejected() -> None:
    registry = EngineRegistry()
    registry.register("fake", FakeTTSEngine, FakeTTSEngine.INFO)

    with pytest.raises(ValidationError, match="đã được đăng ký"):
        registry.register("fake", FakeTTSEngine, FakeTTSEngine.INFO)


def test_unknown_engine_raises_application_error() -> None:
    registry = EngineRegistry()

    with pytest.raises(EngineNotFoundError, match="missing"):
        registry.create("missing")


def test_listing_metadata_does_not_invoke_provider() -> None:
    registry = EngineRegistry()
    calls = 0

    def provider() -> FakeTTSEngine:
        nonlocal calls
        calls += 1
        return FakeTTSEngine()

    registry.register("fake", provider, FakeTTSEngine.INFO)

    assert registry.list_engine_ids() == ["fake"]
    assert registry.list_engine_info() == [FakeTTSEngine.INFO]
    assert calls == 0

