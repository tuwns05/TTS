"""Generic cancellable QRunnable around an application callable."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import CancelledError
from inspect import Parameter, signature
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
        self._inject_cancel_event = self._accepts_cancel_event(function)
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

    def cancel(self) -> None:
        """Request cooperative cancellation without terminating the thread."""

        self._cancel_event.set()

    def is_cancelled(self) -> bool:
        """Return whether cancellation has been requested."""

        return self._cancel_event.is_set()

    @property
    def cancel_event(self) -> Event:
        """Expose the cooperative token passed to cancellation-aware callables."""

        return self._cancel_event

    @staticmethod
    def _accepts_cancel_event(function: Callable[..., object]) -> bool:
        """Return whether a callable explicitly opts into the cancellation token."""

        try:
            parameter = signature(function).parameters.get("cancel_event")
        except (TypeError, ValueError):
            return False
        return parameter is not None and parameter.kind in {
            Parameter.POSITIONAL_OR_KEYWORD,
            Parameter.KEYWORD_ONLY,
        }

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
            kwargs = self._kwargs
            if self._inject_cancel_event:
                kwargs = {**kwargs, "cancel_event": self._cancel_event}
            result = self._function(*self._args, **kwargs)
            if self.is_cancelled():
                self.signals.cancelled.emit()
            else:
                self.signals.result.emit(result)
        except CancelledError:
            self.signals.cancelled.emit()
        except AppError as exc:
            logger.opt(exception=exc).warning(
                "Tác vụ nền thất bại: {}", type(exc).__name__
            )
            self.signals.error.emit(str(exc))
        except Exception:
            logger.exception("Lỗi kỹ thuật không mong đợi trong tác vụ nền")
            self.signals.error.emit("Đã xảy ra lỗi kỹ thuật. Vui lòng kiểm tra nhật ký.")
        finally:
            self.signals.finished.emit()
