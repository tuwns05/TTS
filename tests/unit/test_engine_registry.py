"""Tests for lazy engine registration."""

import pytest

from vntts.engines.factory import EngineRegistry
from vntts.engines.fake_engine import FakeTTSEngine
from vntts.utils.exceptions import EngineNotFoundError, ValidationError


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


def test_registry_returns_registered_capabilities_without_provider_call() -> None:
    registry = EngineRegistry()
    calls = 0

    def provider() -> FakeTTSEngine:
        nonlocal calls
        calls += 1
        return FakeTTSEngine()

    registry.register(
        "fake",
        provider,
        FakeTTSEngine.INFO,
        FakeTTSEngine.CAPABILITIES,
    )

    assert registry.get_capabilities("fake") == FakeTTSEngine.CAPABILITIES
    assert calls == 0
