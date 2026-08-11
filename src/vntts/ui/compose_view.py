"""State, commands and widgets for the speech composition view."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QObject, QRectF, QSize, QThreadPool, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPaintEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from vntts.config.settings import Settings
from vntts.config.theme import THEME
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
from vntts.services.document_import import DocumentTextImporter, ImportedDocument
from vntts.services.synthesis import SynthesizeSpeech
from vntts.services.voice_enrollment import VoiceEnrollmentService
from vntts.services.voice_profiles import VoiceProfile
from vntts.utils.exceptions import AppError, ValidationError
from vntts.utils.worker import TaskWorker


class MainViewModel(QObject):
    """Coordinate main-screen state without importing concrete TTS SDKs."""

    state_changed = Signal(str)
    voices_changed = Signal(object)
    capabilities_changed = Signal(object)
    synthesis_completed = Signal(object)
    document_imported = Signal(object)
    voice_profile_created = Signal(object)
    error_occurred = Signal(str)

    VALID_STATES = {
        "idle",
        "loading_engine",
        "importing_document",
        "synthesizing",
        "enrolling_voice",
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
        document_importer: DocumentTextImporter | None = None,
        voice_enrollment_service: VoiceEnrollmentService | None = None,
    ) -> None:
        super().__init__()
        self._registry = registry
        self._synthesize_speech = synthesize_speech
        self._settings = settings
        self._recommendation = recommendation
        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        self._document_importer = document_importer or DocumentTextImporter()
        self._voice_enrollment_service = voice_enrollment_service
        self._active_workers: set[TaskWorker] = set()
        self._current_worker: TaskWorker | None = None
        self._state = "idle"
        self._selected_engine_id: str | None = None
        self._voices: list[VoiceInfo] = []
        self._selected_capabilities: EngineCapabilities | None = None
        self._state_before_document_import = "idle"

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

    def synthesize(
        self,
        text: str,
        effects: AudioEffects,
        voice_id: str | None,
        style_id: str = "tu_nhien",
        reference_audio_path: str | None = None,
        voice_artifact_path: str | None = None,
        engine_id_override: str | None = None,
    ) -> None:
        """Build a request and execute synthesis outside the UI thread."""

        try:
            engine_id = engine_id_override or self._selected_engine_id
            if engine_id is None:
                raise ValidationError("Vui lòng chọn engine.")
            if voice_id is None:
                raise ValidationError("Vui lòng chọn giọng đọc.")
            if (
                voice_id.startswith("clone:")
                and not reference_audio_path
                and not voice_artifact_path
            ):
                raise ValidationError(
                    "Hồ sơ giọng nhân bản không còn dữ liệu đặc điểm giọng. "
                    "Vui lòng tạo lại hồ sơ."
                )
            request = SynthesisRequest(
                text=text,
                engine_id=engine_id,
                options=EngineSynthesisOptions(
                    voice_id=voice_id,
                    reference_audio_path=reference_audio_path,
                    style_id=style_id,
                    voice_artifact_path=voice_artifact_path,
                ),
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

    def enroll_voice(self, name: str, source_audio_path: str) -> None:
        """Extract and persist a cloned voice outside the UI thread."""

        if self._voice_enrollment_service is None:
            self._fail("Chức năng tạo đặc điểm giọng chưa được cấu hình.")
            return
        if self._state in {
            "loading_engine",
            "importing_document",
            "synthesizing",
            "enrolling_voice",
        }:
            self.error_occurred.emit("Vui lòng chờ tác vụ hiện tại hoàn thành.")
            return
        self._set_state("enrolling_voice")
        worker = TaskWorker(
            self._voice_enrollment_service.enroll,
            name,
            source_audio_path,
        )
        worker.signals.result.connect(self._voice_profile_ready)
        worker.signals.error.connect(self._fail)
        worker.signals.cancelled.connect(lambda: self._set_state("cancelled"))
        self._start_worker(worker)

    def import_document(self, source_path: str) -> None:
        """Extract a supported document outside the UI thread."""

        if self._state in {"loading_engine", "importing_document", "synthesizing"}:
            self.error_occurred.emit("Vui lòng chờ tác vụ hiện tại hoàn thành trước khi mở tệp.")
            return
        self._state_before_document_import = self._state
        self._set_state("importing_document")
        worker = TaskWorker(self._document_importer.import_file, source_path)
        worker.signals.result.connect(self._document_ready)
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

    def _voice_profile_ready(self, profile: VoiceProfile) -> None:
        self._set_state("idle")
        self.voice_profile_created.emit(profile)

    def _document_ready(self, document: ImportedDocument) -> None:
        self._set_state(self._state_before_document_import)
        self.document_imported.emit(document)

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
        self.setProperty("card", True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.combo = QComboBox(self)
        self.combo.setObjectName("engineCombo")
        self.combo.setAccessibleName("Engine tổng hợp")
        self.combo.setMinimumHeight(38)
        self.combo.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )
        self.recommendation_label = QLabel(self)
        self.recommendation_label.setObjectName("recommendationLabel")
        self.recommendation_label.setWordWrap(True)
        self.status_badge = QLabel("Đang chờ", self)
        self.status_badge.setObjectName("engineStatus")
        self.status_badge.setProperty("state", "neutral")
        title = QLabel("Engine", self)
        title.setObjectName("sectionTitle")
        title.setProperty("role", "section")
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(self.status_badge)
        field_label = QLabel("Mô hình tổng hợp", self)
        field_label.setObjectName("fieldLabel")
        field_label.hide()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        layout.addLayout(title_row)
        layout.addWidget(self.combo)
        self.recommendation_label.hide()
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
            self.combo.setToolTip("")
            return
        self.combo.setToolTip(
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
    """Expose a compact play/pause toggle and a secondary stop command."""

    play_requested = Signal()
    pause_requested = Signal()
    stop_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.play_button = QPushButton(self)
        self.play_button.setObjectName("playButton")
        self.play_button.setProperty("variant", "primary")
        self.stop_button = QPushButton(self)
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setProperty("variant", "secondary")
        layout.addWidget(self.play_button)
        layout.addWidget(self.stop_button)
        self.play_button.setAccessibleName("Phát audio")
        self.stop_button.setAccessibleName("Dừng audio")
        self.play_button.setIconSize(QSize(20, 20))
        self.stop_button.setIconSize(QSize(15, 15))
        self.stop_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop)
        )
        self.play_button.setToolTip("Phát")
        self.stop_button.setToolTip("Dừng")
        self._state = "empty"
        self.play_button.clicked.connect(self._toggle_play_pause)
        self.stop_button.clicked.connect(self.stop_requested)
        self.set_playback_state("empty")

    def set_playback_state(self, state: str) -> None:
        """Enable only commands valid for the current playback state."""

        self._state = state
        has_audio = state != "empty"
        is_playing = state == "playing"
        media_icon = (
            QStyle.StandardPixmap.SP_MediaPause
            if is_playing
            else QStyle.StandardPixmap.SP_MediaPlay
        )
        self.play_button.setIcon(self.style().standardIcon(media_icon))
        self.play_button.setAccessibleName("Tạm dừng audio" if is_playing else "Phát audio")
        self.play_button.setToolTip("Tạm dừng" if is_playing else "Phát")
        self.play_button.setProperty("playing", is_playing)
        self.play_button.style().unpolish(self.play_button)
        self.play_button.style().polish(self.play_button)
        self.play_button.setEnabled(has_audio)
        self.stop_button.setEnabled(state in {"playing", "paused"})

    def _toggle_play_pause(self) -> None:
        if self._state == "playing":
            self.pause_requested.emit()
        else:
            self.play_requested.emit()


class WaveformCanvas(QWidget):
    """Paint an amplitude waveform and translate pointer movement into seeking."""

    seek_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("waveformCanvas")
        self.setAccessibleName("Dải sóng âm thanh")
        self.setMinimumHeight(54)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._envelope = np.zeros(96, dtype=np.float32)
        self._duration_ms = 0
        self._position_ms = 0
        self._has_audio = False

    def sizeHint(self) -> QSize:
        return QSize(420, 54)

    def set_audio(self, result: SynthesisResult, duration_ms: int) -> None:
        audio = np.abs(np.asarray(result.audio, dtype=np.float32))
        chunks = np.array_split(audio, min(192, max(1, audio.size)))
        peaks = np.array([float(chunk.max(initial=0.0)) for chunk in chunks])
        reference = float(np.percentile(peaks, 95)) if peaks.size else 0.0
        if reference > 0:
            peaks = np.clip(peaks / reference, 0.0, 1.0)
        self._envelope = peaks.astype(np.float32)
        self._duration_ms = max(0, int(duration_ms))
        self._position_ms = 0
        self._has_audio = self._duration_ms > 0
        self.setCursor(
            Qt.CursorShape.PointingHandCursor
            if self._has_audio
            else Qt.CursorShape.ArrowCursor
        )
        self.update()

    def clear(self) -> None:
        self._envelope = np.zeros(96, dtype=np.float32)
        self._duration_ms = 0
        self._position_ms = 0
        self._has_audio = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def set_position(self, position_ms: int) -> None:
        self._position_ms = max(0, min(int(position_ms), self._duration_ms))
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bounds = self.rect().adjusted(3, 5, -3, -5)
        if bounds.width() <= 0 or bounds.height() <= 0:
            return

        bar_step = 5
        bar_width = 2.25
        count = max(1, bounds.width() // bar_step)
        source_indices = np.linspace(0, self._envelope.size - 1, count).astype(int)
        values = self._envelope[source_indices]
        progress = (
            self._position_ms / self._duration_ms
            if self._has_audio and self._duration_ms
            else 0.0
        )
        center_y = bounds.center().y()
        maximum_height = max(10.0, bounds.height() * 0.82)

        painter.setPen(Qt.PenStyle.NoPen)
        for index, amplitude in enumerate(values):
            fraction = index / max(1, count - 1)
            height = 8.0 + float(amplitude) * (maximum_height - 8.0)
            x = bounds.left() + index * bar_step
            color = THEME.accent if self._has_audio and fraction <= progress else THEME.border
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(
                QRectF(x, center_y - height / 2, bar_width, height),
                1.2,
                1.2,
            )

        if self._has_audio:
            playhead_x = bounds.left() + progress * bounds.width()
            painter.setPen(QPen(QColor(THEME.accent), 2.0))
            painter.drawLine(int(playhead_x), bounds.top(), int(playhead_x), bounds.bottom())

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._seek_from_x(event.position().x())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._seek_from_x(event.position().x())
        super().mouseMoveEvent(event)

    def _seek_from_x(self, x_position: float) -> None:
        if not self._has_audio or self.width() <= 0:
            return
        fraction = max(0.0, min(1.0, x_position / self.width()))
        position = round(fraction * self._duration_ms)
        self.set_position(position)
        self.seek_requested.emit(position)


class WaveformPreview(QWidget):
    """Combine elapsed time, a real waveform and total clip duration."""

    seek_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("audioTimeline")
        self.setMinimumHeight(52)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._has_audio = False
        self._duration_ms = 0
        self.canvas = WaveformCanvas(self)
        self.canvas.seek_requested.connect(self.seek_requested)
        self.elapsed_label = QLabel("00:00", self)
        self.elapsed_label.setObjectName("elapsedTime")
        self.duration_label = QLabel("00:00", self)
        self.duration_label.setObjectName("durationTime")

        timeline = QHBoxLayout()
        timeline.setContentsMargins(0, 0, 0, 0)
        timeline.setSpacing(14)
        timeline.addWidget(self.elapsed_label)
        timeline.addWidget(self.canvas, 1)
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
        self.canvas.set_audio(result, self._duration_ms)
        self.elapsed_label.setText("00:00")
        self.duration_label.setText(self._format_time(self._duration_ms))

    def clear(self) -> None:
        """Return to the disabled empty-audio state."""

        self._has_audio = False
        self._duration_ms = 0
        self.canvas.clear()
        self.elapsed_label.setText("00:00")
        self.duration_label.setText("00:00")

    def set_position(self, position_ms: int) -> None:
        """Update playback progress without fighting an active drag gesture."""

        position = max(0, min(int(position_ms), self._duration_ms))
        self.canvas.set_position(position)
        self.elapsed_label.setText(self._format_time(position))

    @staticmethod
    def _format_time(milliseconds: int) -> str:
        seconds = max(0, int(milliseconds)) // 1_000
        minutes, seconds = divmod(seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"


class TextInputWidget(QWidget):
    """Collect Vietnamese text and display its current length."""

    text_changed = Signal(str)
    open_file_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("textInputPanel")
        self.editor = QPlainTextEdit(self)
        self.editor.setObjectName("textInput")
        self.editor.setPlaceholderText("Nhập văn bản cần tạo giọng nói...")
        self.editor.setAccessibleName("Nội dung")
        self.editor.setMinimumHeight(180)
        self.editor.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Expanding,
        )
        self.character_count = QLabel(self)
        self.character_count.setObjectName("characterCount")
        self.open_file_button = QPushButton("Mở tệp", self)
        self.open_file_button.setObjectName("openFileButton")
        self.open_file_button.setProperty("variant", "secondary")
        self.open_file_button.setAccessibleName("Mở tệp văn bản")
        self.open_file_button.setToolTip("Nhập nội dung từ TXT, SRT, DOCX hoặc PDF")

        title = QLabel("Nội dung", self)
        title.setObjectName("sectionTitle")
        title.setProperty("role", "section")
        helper = QLabel("Nhập hoặc dán nội dung cần chuyển thành giọng nói.", self)
        helper.setObjectName("helperText")
        helper.setProperty("role", "secondary")
        helper.setWordWrap(True)
        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.open_file_button)
        header.addWidget(self.character_count)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addLayout(header)
        layout.addWidget(helper)
        layout.addWidget(self.editor)
        self.open_file_button.clicked.connect(self.open_file_requested)
        self.editor.textChanged.connect(self._on_text_changed)
        self._on_text_changed()

    def text(self) -> str:
        """Return the current plain text."""

        return self.editor.toPlainText()

    def set_text(self, text: str) -> None:
        """Replace editor contents with imported plain text."""

        self.editor.setPlainText(text)

    def _on_text_changed(self) -> None:
        value = self.text()
        formatted_count = f"{len(value):,}".replace(",", ".")
        self.character_count.setText(f"{formatted_count} ký tự")
        self.text_changed.emit(value)
