"""Tests for the engine factory boundary."""

import pytest

from vntts.engines.factory import EngineFactory, EngineRegistry
from vntts.utils.exceptions import EngineNotFoundError
from tests.stubs import StubTTSEngine


def _factory() -> EngineFactory:
    registry = EngineRegistry()
    registry.register("stub", StubTTSEngine, StubTTSEngine.INFO)
    return EngineFactory(registry)


def test_factory_creates_correct_engine() -> None:
    assert isinstance(_factory().create("stub"), StubTTSEngine)


def test_factory_returns_independent_instances() -> None:
    factory = _factory()
    first = factory.create("stub")
    second = factory.create("stub")

    assert first is not second


def test_factory_rejects_unknown_engine_id() -> None:
    with pytest.raises(EngineNotFoundError):
        _factory().create("unknown")
