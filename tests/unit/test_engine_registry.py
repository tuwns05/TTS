"""Tests for lazy engine registration."""

import pytest

from vntts.engines.factory import EngineRegistry
from vntts.utils.exceptions import EngineNotFoundError, ValidationError
from tests.stubs import StubTTSEngine


def test_register_and_create_engine() -> None:
    registry = EngineRegistry()
    registry.register("stub", StubTTSEngine, StubTTSEngine.INFO)

    assert registry.contains("stub")
    assert isinstance(registry.create("stub"), StubTTSEngine)


def test_duplicate_engine_id_is_rejected() -> None:
    registry = EngineRegistry()
    registry.register("stub", StubTTSEngine, StubTTSEngine.INFO)

    with pytest.raises(ValidationError, match="đã được đăng ký"):
        registry.register("stub", StubTTSEngine, StubTTSEngine.INFO)


def test_unknown_engine_raises_application_error() -> None:
    registry = EngineRegistry()

    with pytest.raises(EngineNotFoundError, match="missing"):
        registry.create("missing")


def test_listing_metadata_does_not_invoke_provider() -> None:
    registry = EngineRegistry()
    calls = 0

    def provider() -> StubTTSEngine:
        nonlocal calls
        calls += 1
        return StubTTSEngine()

    registry.register("stub", provider, StubTTSEngine.INFO)

    assert registry.list_engine_ids() == ["stub"]
    assert registry.list_engine_info() == [StubTTSEngine.INFO]
    assert calls == 0


def test_registry_returns_registered_capabilities_without_provider_call() -> None:
    registry = EngineRegistry()
    calls = 0

    def provider() -> StubTTSEngine:
        nonlocal calls
        calls += 1
        return StubTTSEngine()

    registry.register(
        "stub",
        provider,
        StubTTSEngine.INFO,
        StubTTSEngine.CAPABILITIES,
    )

    assert registry.get_capabilities("stub") == StubTTSEngine.CAPABILITIES
    assert calls == 0
