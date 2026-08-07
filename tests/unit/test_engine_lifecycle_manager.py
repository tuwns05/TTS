"""Tests for single-active-engine lifecycle coordination."""

from vntts.db.models import EngineInfo
from vntts.engines.factory import EngineFactory, EngineLifecycleManager, EngineRegistry
from vntts.engines.fake_engine import FakeTTSEngine


class _TrackingFake(FakeTTSEngine):
    def __init__(self, engine_id: str) -> None:
        super().__init__(processing_delay=0)
        self._info = EngineInfo(engine_id, engine_id)
        self.unload_count = 0

    @property
    def engine_info(self) -> EngineInfo:
        return self._info

    def unload(self) -> None:
        self.unload_count += 1
        super().unload()


def test_switching_engine_unloads_previous_instance() -> None:
    registry = EngineRegistry()
    first = _TrackingFake("first")
    second = _TrackingFake("second")
    registry.register("first", lambda: first, first.engine_info, first.capabilities)
    registry.register("second", lambda: second, second.engine_info, second.capabilities)
    lifecycle = EngineLifecycleManager(EngineFactory(registry))

    lifecycle.activate("first")
    lifecycle.activate("second")

    assert not first.is_loaded()
    assert first.unload_count == 1
    assert second.is_loaded()
    assert lifecycle.active_engine_id == "second"


def test_reactivating_same_engine_does_not_reload_or_recreate() -> None:
    registry = EngineRegistry()
    engine = _TrackingFake("only")
    calls = 0

    def provider() -> _TrackingFake:
        nonlocal calls
        calls += 1
        return engine

    registry.register("only", provider, engine.engine_info, engine.capabilities)
    lifecycle = EngineLifecycleManager(EngineFactory(registry))

    assert lifecycle.activate("only") is lifecycle.activate("only")
    assert calls == 1


def test_unload_all_releases_and_forgets_adapters() -> None:
    registry = EngineRegistry()
    engine = _TrackingFake("only")
    registry.register("only", lambda: engine, engine.engine_info, engine.capabilities)
    lifecycle = EngineLifecycleManager(EngineFactory(registry))
    lifecycle.activate("only")

    lifecycle.unload_all()

    assert lifecycle.active_engine_id is None
    assert not engine.is_loaded()
