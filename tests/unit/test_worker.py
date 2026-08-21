"""Tests for cooperative background-worker cancellation."""

from concurrent.futures import CancelledError
from threading import Event

from vntts.utils.worker import TaskWorker


def test_worker_passes_its_event_to_aware_callable() -> None:
    received: list[Event | None] = []
    results: list[object] = []

    def operation(*, cancel_event: Event | None = None) -> str:
        received.append(cancel_event)
        return "done"

    worker = TaskWorker(operation)
    worker.signals.result.connect(results.append)
    worker.run()

    assert received == [worker.cancel_event]
    assert results == ["done"]


def test_worker_emits_cancelled_instead_of_error_for_cancelled_error() -> None:
    cancelled: list[bool] = []
    errors: list[str] = []

    def operation(*, cancel_event: Event | None = None) -> None:
        assert cancel_event is not None
        raise CancelledError()

    worker = TaskWorker(operation)
    worker.signals.cancelled.connect(lambda: cancelled.append(True))
    worker.signals.error.connect(errors.append)
    worker.run()

    assert cancelled == [True]
    assert errors == []
