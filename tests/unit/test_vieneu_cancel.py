"""Tests for VieNeu frame-boundary cancellation compatibility."""

from __future__ import annotations

import sys
from concurrent.futures import CancelledError
from threading import Event
from types import ModuleType

import pytest

from vntts.engines.vieneu_cancel import install_vieneu_cancel_support


def test_static_batch_keeps_batch_and_stops_before_next_frame(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cancel_event = Event()
    module_name = "tests.fake_vieneu_batch_engine"
    batch_module = ModuleType(module_name)
    frame_calls = 0

    def generate_frame_batched() -> None:
        nonlocal frame_calls
        frame_calls += 1
        cancel_event.set()

    batch_module.generate_frame_batched = generate_frame_batched  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, module_name, batch_module)
    batch_type = type("BatchEngine", (), {"__module__": module_name})
    batch_engine = batch_type()

    class Runtime:
        def __init__(self) -> None:
            self.engine = object()
            self._batch_engine = batch_engine
            self.infer_calls = 0
            self.received_cancel_event: object = None

        def _get_batch_engine(self) -> object:
            return self._batch_engine

        def infer(self, **kwargs: object) -> None:
            self.infer_calls += 1
            self.received_cancel_event = kwargs.get("cancel_event")
            assert self._get_batch_engine() is batch_engine
            for _ in range(5):
                batch_module.generate_frame_batched()  # type: ignore[attr-defined]

    runtime = Runtime()
    install_vieneu_cancel_support(runtime)

    with pytest.raises(CancelledError):
        runtime.infer(cancel_event=cancel_event)

    assert runtime.received_cancel_event is cancel_event
    assert runtime.infer_calls == 1
    assert frame_calls == 1
    assert runtime._batch_engine is batch_engine
