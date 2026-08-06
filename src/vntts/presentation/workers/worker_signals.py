"""Signals emitted by a generic background task."""

from PySide6.QtCore import QObject, Signal


class WorkerSignals(QObject):
    """Thread-safe communication from a worker to the presentation layer."""

    started = Signal()
    progress = Signal(int, str)
    result = Signal(object)
    error = Signal(str)
    cancelled = Signal()
    finished = Signal()

