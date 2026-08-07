"""Generic cancellable QRunnable around an application callable."""

from __future__ import annotations

from collections.abc import Callable
from threading import Event
from typing import Generic, ParamSpec, TypeVar

from loguru import logger
from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from vntts.utils.exceptions import AppError

P = ParamSpec("P")
R = TypeVar("R")


class WorkerSignals(QObject):
    """Thread-safe communication from a worker to the presentation layer."""

    started = Signal()
    progress = Signal(int, str)
    result = Signal(object)
    error = Signal(str)
    cancelled = Signal()
    finished = Signal()


class TaskWorker(QRunnable, Generic[P, R]):
    """Run one callable outside the UI thread and report through Qt signals."""

    def __init__(self, function: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> None:
        super().__init__()
        self._function = function
        self._args = args
        self._kwargs = kwargs
        self._cancel_event = Event()
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

    def cancel(self) -> None:
        """Request cooperative cancellation without terminating the thread."""

        self._cancel_event.set()

    def is_cancelled(self) -> bool:
        """Return whether cancellation has been requested."""

        return self._cancel_event.is_set()

    def report_progress(self, percent: int, message: str = "") -> None:
        """Emit bounded progress for callables that explicitly report it."""

        self.signals.progress.emit(max(0, min(100, percent)), message)

    @Slot()
    def run(self) -> None:
        """Execute the callable and translate failures into friendly messages."""

        self.signals.started.emit()
        try:
            if self.is_cancelled():
                self.signals.cancelled.emit()
                return
            result = self._function(*self._args, **self._kwargs)
            if self.is_cancelled():
                self.signals.cancelled.emit()
            else:
                self.signals.result.emit(result)
        except AppError as exc:
            logger.warning("Tác vụ nền thất bại: {}", type(exc).__name__)
            self.signals.error.emit(str(exc))
        except Exception:
            logger.exception("Lỗi kỹ thuật không mong đợi trong tác vụ nền")
            self.signals.error.emit("Đã xảy ra lỗi kỹ thuật. Vui lòng kiểm tra nhật ký.")
        finally:
            self.signals.finished.emit()
