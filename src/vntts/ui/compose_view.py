"""State, commands and widgets for the speech composition view."""

from __future__ import annotations

from PySide6.QtCore import QObject, QThreadPool, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from vntts.config.settings import Settings
from vntts.db.models import (
    AudioEffects,
    EngineInfo,
    EngineRecommendation,
    EngineSynthesisOptions,
    SynthesisRequest,
    SynthesisResult,
    VoiceInfo,
)
from vntts.engines.base import EngineCapabilities
from vntts.engines.factory import EngineRegistry
from vntts.services.synthesis import SynthesizeSpeech
from vntts.utils.exceptions import AppError, ValidationError
from vntts.utils.worker import TaskWorker


class MainViewModel(QObject):
    """Coordinate main-screen state without importing concrete TTS SDKs."""

    state_changed = Signal(str)
    voices_changed = Signal(object)
    capabilities_changed = Signal(object)
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
        self._selected_capabilities: EngineCapabilities | None = None

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

    @property
    def selected_capabilities(self) -> EngineCapabilities | None:
        """Return capabilities for the selected registered adapter."""

        return self._selected_capabilities

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
        self._selected_capabilities = self._registry.get_capabilities(engine_id)
        self.capabilities_changed.emit(self._selected_capabilities)
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


class EngineSelector(QWidget):
    """Display only registered engines and an optional recommendation."""

    engine_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("enginePanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.combo = QComboBox(self)
        self.combo.setObjectName("engineCombo")
        self.combo.setAccessibleName("Engine tổng hợp")
        self.combo.setMinimumHeight(44)
        self.recommendation_label = QLabel(self)
        self.recommendation_label.setObjectName("recommendationLabel")
        self.recommendation_label.setWordWrap(True)
        self.status_badge = QLabel("Đang chờ", self)
        self.status_badge.setObjectName("engineStatus")
        self.status_badge.setProperty("state", "neutral")
        title = QLabel("Engine", self)
        title.setObjectName("sectionTitle")
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(self.status_badge)
        field_label = QLabel("Mô hình tổng hợp", self)
        field_label.setObjectName("fieldLabel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(8)
        layout.addLayout(title_row)
        layout.addSpacing(8)
        layout.addWidget(field_label)
        layout.addWidget(self.combo)
        layout.addWidget(self.recommendation_label)
        self.combo.currentIndexChanged.connect(self._emit_current_engine)

    def set_engines(self, engines: list[EngineInfo], selected_id: str | None = None) -> None:
        """Replace choices using metadata already cached by the registry."""

        self.combo.blockSignals(True)
        self.combo.clear()
        selected_index = 0
        for index, engine in enumerate(engines):
            self.combo.addItem(engine.display_name, engine.engine_id)
            if engine.engine_id == selected_id:
                selected_index = index
        if self.combo.count():
            self.combo.setCurrentIndex(selected_index)
        self.combo.blockSignals(False)

    def set_recommendation(self, recommendation: EngineRecommendation | None) -> None:
        """Show a non-binding recommendation without adding unregistered engines."""

        if recommendation is None:
            self.recommendation_label.clear()
            self.recommendation_label.hide()
            return
        self.recommendation_label.show()
        self.recommendation_label.setText(
            f"Khuyến nghị khi khả dụng: {recommendation.engine_id} — {recommendation.reason}"
        )

    def current_engine_id(self) -> str | None:
        """Return the selected registered engine identifier."""

        value = self.combo.currentData()
        return str(value) if value is not None else None

    def set_status(self, text: str, state: str) -> None:
        """Keep engine state adjacent to the engine it describes."""

        self.status_badge.setText(text)
        self.status_badge.setProperty("state", state)
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)

    def _emit_current_engine(self) -> None:
        engine_id = self.current_engine_id()
        if engine_id is not None:
            self.engine_changed.emit(engine_id)


class PlaybackControls(QWidget):
    """Expose Play/Pause/Stop commands and reflect playback state."""

    play_requested = Signal()
    pause_requested = Signal()
    stop_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.play_button = QPushButton("▶", self)
        self.play_button.setObjectName("playButton")
        self.pause_button = QPushButton("Ⅱ", self)
        self.pause_button.setObjectName("pauseButton")
        self.stop_button = QPushButton("■", self)
        self.stop_button.setObjectName("stopButton")
        for button in (self.play_button, self.pause_button, self.stop_button):
            layout.addWidget(button)
        layout.addStretch()
        self.play_button.setAccessibleName("Phát audio")
        self.pause_button.setAccessibleName("Tạm dừng audio")
        self.stop_button.setAccessibleName("Dừng audio")
        self.play_button.setToolTip("Phát")
        self.pause_button.setToolTip("Tạm dừng")
        self.stop_button.setToolTip("Dừng")
        self.play_button.clicked.connect(self.play_requested)
        self.pause_button.clicked.connect(self.pause_requested)
        self.stop_button.clicked.connect(self.stop_requested)
        self.set_playback_state("empty")

    def set_playback_state(self, state: str) -> None:
        """Enable only commands valid for the current playback state."""

        has_audio = state != "empty"
        self.play_button.setEnabled(has_audio and state != "playing")
        self.pause_button.setEnabled(state == "playing")
        self.stop_button.setEnabled(state in {"playing", "paused"})


class WaveformPreview(QWidget):
    """Interactive single-track scrubber retained under the legacy class name."""

    seek_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("audioTimeline")
        self.setMinimumHeight(52)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._has_audio = False
        self._duration_ms = 0
        self.slider = QSlider(Qt.Orientation.Horizontal, self)
        self.slider.setObjectName("playbackScrubber")
        self.slider.setAccessibleName("Vị trí phát audio")
        self.slider.setRange(0, 0)
        self.slider.setEnabled(False)
        self.slider.sliderMoved.connect(self.seek_requested)
        self.elapsed_label = QLabel("00:00", self)
        self.elapsed_label.setObjectName("timeLabel")
        self.duration_label = QLabel("00:00", self)
        self.duration_label.setObjectName("timeLabel")

        timeline = QHBoxLayout()
        timeline.setContentsMargins(0, 0, 0, 0)
        timeline.setSpacing(10)
        timeline.addWidget(self.elapsed_label)
        timeline.addWidget(self.slider, 1)
        timeline.addWidget(self.duration_label)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(timeline)

    @property
    def has_audio(self) -> bool:
        """Return whether a waveform is available for rendering."""

        return self._has_audio

    def set_result(self, result: SynthesisResult) -> None:
        """Prepare the scrubber using the synthesized clip duration."""

        duration_ms = round(result.audio.size / result.sample_rate * 1_000)
        self._has_audio = duration_ms > 0
        self._duration_ms = max(0, duration_ms)
        self.slider.setRange(0, self._duration_ms)
        self.slider.setValue(0)
        self.slider.setEnabled(self._has_audio)
        self.elapsed_label.setText("00:00")
        self.duration_label.setText(self._format_time(self._duration_ms))

    def clear(self) -> None:
        """Return to the disabled empty-audio state."""

        self._has_audio = False
        self._duration_ms = 0
        self.slider.setRange(0, 0)
        self.slider.setValue(0)
        self.slider.setEnabled(False)
        self.elapsed_label.setText("00:00")
        self.duration_label.setText("00:00")

    def set_position(self, position_ms: int) -> None:
        """Update playback progress without fighting an active drag gesture."""

        position = max(0, min(int(position_ms), self._duration_ms))
        if not self.slider.isSliderDown():
            self.slider.setValue(position)
        self.elapsed_label.setText(self._format_time(position))

    @staticmethod
    def _format_time(milliseconds: int) -> str:
        seconds = max(0, int(milliseconds)) // 1_000
        minutes, seconds = divmod(seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"


class TextInputWidget(QWidget):
    """Collect Vietnamese text and display its current length."""

    text_changed = Signal(str)

    def __init__(self, max_length: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("textInputPanel")
        self._max_length = max_length
        self.editor = QPlainTextEdit(self)
        self.editor.setObjectName("textInput")
        self.editor.setPlaceholderText("Nhập văn bản tiếng Việt cần tổng hợp...")
        self.editor.setAccessibleName("Nội dung tiếng Việt")
        self.editor.setMinimumHeight(280)
        self.character_count = QLabel(self)
        self.character_count.setObjectName("characterCount")

        title = QLabel("Nội dung tiếng Việt", self)
        title.setObjectName("sectionTitle")
        helper = QLabel("Nhập hoặc dán nội dung cần chuyển thành giọng nói.", self)
        helper.setObjectName("helperText")
        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.character_count)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addLayout(header)
        layout.addWidget(helper)
        layout.addWidget(self.editor)
        self.editor.textChanged.connect(self._on_text_changed)
        self._on_text_changed()

    def text(self) -> str:
        """Return the current plain text."""

        return self.editor.toPlainText()

    def _on_text_changed(self) -> None:
        value = self.text()
        self.character_count.setText(f"{len(value)} / {self._max_length} ký tự")
        self.text_changed.emit(value)
