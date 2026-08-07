"""State and commands for the main application window."""

from __future__ import annotations

from PySide6.QtCore import QObject, QThreadPool, Signal

from vntts.application.services.engine_registry import EngineRegistry
from vntts.application.use_cases.synthesize_speech import SynthesizeSpeech
from vntts.config.settings import Settings
from vntts.domain.exceptions import AppError, ValidationError
from vntts.domain.hardware.models import EngineRecommendation
from vntts.domain.tts.models import (
    AudioEffects,
    EngineInfo,
    EngineSynthesisOptions,
    SynthesisRequest,
    SynthesisResult,
    VoiceInfo,
)
from vntts.presentation.workers.task_worker import TaskWorker


class MainViewModel(QObject):
    """Coordinate main-screen state without importing concrete TTS SDKs."""

    state_changed = Signal(str)
    voices_changed = Signal(object)
    synthesis_completed = Signal(object)
    error_occurred = Signal(str)

    VALID_STATES = {
        "idle",
        "loading_engine",
        "synthesizing",
        "completed",
        "error",
        "cancelled",
    }

    def __init__(
        self,
        registry: EngineRegistry,
        synthesize_speech: SynthesizeSpeech,
        settings: Settings,
        recommendation: EngineRecommendation | None = None,
        thread_pool: QThreadPool | None = None,
    ) -> None:
        super().__init__()
        self._registry = registry
        self._synthesize_speech = synthesize_speech
        self._settings = settings
        self._recommendation = recommendation
        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        self._active_workers: set[TaskWorker] = set()
        self._current_worker: TaskWorker | None = None
        self._state = "idle"
        self._selected_engine_id: str | None = None
        self._voices: list[VoiceInfo] = []

    @property
    def state(self) -> str:
        """Return the current presentation state."""

        return self._state

    @property
    def engine_infos(self) -> list[EngineInfo]:
        """Return registered engine metadata without creating engines."""

        return self._registry.list_engine_info()

    @property
    def recommendation(self) -> EngineRecommendation | None:
        """Return the non-binding runtime recommendation."""

        return self._recommendation

    @property
    def selected_engine_id(self) -> str | None:
        """Return the engine selected by the user."""

        return self._selected_engine_id

    @property
    def voices(self) -> list[VoiceInfo]:
        """Return voices loaded for the current engine."""

        return list(self._voices)

    def initialize(self) -> None:
        """Select and load the configured engine asynchronously."""

        engine_ids = self._registry.list_engine_ids()
        if not engine_ids:
            self._fail("Không có engine nào được đăng ký.")
            return
        default_id = self._settings.tts.default_engine
        self.select_engine(default_id if self._registry.contains(default_id) else engine_ids[0])

    def select_engine(self, engine_id: str) -> None:
        """Load the selected engine in a worker and publish its voices."""

        if not self._registry.contains(engine_id):
            self._fail(f"Không tìm thấy engine '{engine_id}'.")
            return
        self.cancel_current_task()
        self._selected_engine_id = engine_id
        self._voices = []
        self.voices_changed.emit([])
        self._set_state("loading_engine")
        worker = TaskWorker(self._synthesize_speech.prepare_engine, engine_id)
        worker.signals.result.connect(
            lambda voices, selected=engine_id: self._engine_ready(selected, voices)
        )
        worker.signals.error.connect(self._fail)
        worker.signals.cancelled.connect(lambda: self._set_state("cancelled"))
        self._start_worker(worker)

    def synthesize(self, text: str, effects: AudioEffects, voice_id: str | None) -> None:
        """Build a request and execute synthesis outside the UI thread."""

        try:
            if self._selected_engine_id is None:
                raise ValidationError("Vui lòng chọn engine.")
            if voice_id is None:
                raise ValidationError("Vui lòng chọn giọng đọc.")
            request = SynthesisRequest(
                text=text,
                engine_id=self._selected_engine_id,
                options=EngineSynthesisOptions(voice_id=voice_id),
                effects=effects,
            )
        except AppError as exc:
            self._fail(str(exc))
            return

        self._set_state("synthesizing")
        worker = TaskWorker(self._synthesize_speech.execute, request)
        worker.signals.result.connect(self._synthesis_ready)
        worker.signals.error.connect(self._fail)
        worker.signals.cancelled.connect(lambda: self._set_state("cancelled"))
        self._start_worker(worker)

    def cancel_current_task(self) -> None:
        """Request cooperative cancellation of the current worker."""

        if self._current_worker is not None:
            self._current_worker.cancel()

    def shutdown(self) -> None:
        """Cancel work, wait briefly and release cached engines."""

        for worker in tuple(self._active_workers):
            worker.cancel()
        self._thread_pool.waitForDone(2_000)
        self._synthesize_speech.unload_all()

    def _start_worker(self, worker: TaskWorker) -> None:
        self._active_workers.add(worker)
        self._current_worker = worker
        worker.signals.finished.connect(lambda current=worker: self._worker_finished(current))
        self._thread_pool.start(worker)

    def _worker_finished(self, worker: TaskWorker) -> None:
        self._active_workers.discard(worker)
        if self._current_worker is worker:
            self._current_worker = None

    def _engine_ready(self, engine_id: str, voices: list[VoiceInfo]) -> None:
        if engine_id != self._selected_engine_id:
            return
        self._voices = list(voices)
        self.voices_changed.emit(self.voices)
        self._set_state("idle")

    def _synthesis_ready(self, result: SynthesisResult) -> None:
        self._set_state("completed")
        self.synthesis_completed.emit(result)

    def _fail(self, message: str) -> None:
        self._set_state("error")
        self.error_occurred.emit(message)

    def _set_state(self, state: str) -> None:
        if state not in self.VALID_STATES:
            raise ValueError(f"Unknown view state: {state}")
        self._state = state
        self.state_changed.emit(state)

