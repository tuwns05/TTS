"""Tests for the engine factory boundary."""

import pytest

from vntts.engines.factory import EngineFactory, EngineRegistry
from vntts.engines.fake_engine import FakeTTSEngine
from vntts.utils.exceptions import EngineNotFoundError


def _factory() -> EngineFactory:
    registry = EngineRegistry()
    registry.register("fake", FakeTTSEngine, FakeTTSEngine.INFO)
    return EngineFactory(registry)


def test_factory_creates_correct_engine() -> None:
    assert isinstance(_factory().create("fake"), FakeTTSEngine)


def test_factory_returns_independent_instances() -> None:
    factory = _factory()
    first = factory.create("fake")
    second = factory.create("fake")

    assert first is not second


def test_factory_rejects_unknown_engine_id() -> None:
    with pytest.raises(EngineNotFoundError):
        _factory().create("unknown")
