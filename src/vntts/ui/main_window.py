"""Desktop workspace for the Vietnamese text-to-speech workflow."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QResizeEvent
from PySide6.QtWidgets import (
    QBoxLayout,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from vntts.config.settings import Settings
from vntts.config.theme import build_stylesheet
from vntts.db.models import SynthesisResult
from vntts.services.document_import import ImportedDocument
from vntts.services.playback import PlaybackService
from vntts.utils.exceptions import PlaybackError
from vntts.ui.compose_view import (
    EngineSelector,
    MainViewModel,
    PlaybackControls,
    TextInputWidget,
    WaveformPreview,
)
from vntts.ui.settings_panel import VoiceSelectorWidget, VoiceStyleWidget


class MainWindow(QMainWindow):
    """Compose widgets and reflect state emitted by MainViewModel."""

    def __init__(
        self,
        view_model: MainViewModel,
        settings: Settings,
        playback: PlaybackService | None = None,
    ) -> None:
        super().__init__()
        self._view_model = view_model
        self._settings = settings
        self._playback = playback or PlaybackService(self)
        self.setObjectName("AppRoot")
        self.setWindowTitle(settings.application.name)
        self.resize(1080, 760)
        self.setMinimumSize(640, 560)
        self._responsive_mode = ""

        self.text_input = TextInputWidget(self)
        self.engine_selector = EngineSelector(self)
        self.voice_selector = VoiceSelectorWidget(self)
        self.voice_style = VoiceStyleWidget(settings.audio, self)
        self.playback_controls = PlaybackControls(self)
        self.waveform = WaveformPreview(self)
        self.synthesize_button = QPushButton("Tạo giọng nói", self)
        self.synthesize_button.setObjectName("synthesizeButton")
        self.synthesize_button.setAccessibleName("Tạo giọng nói")
        self.synthesize_button.setMinimumSize(176, 48)
        self.synthesize_button.setEnabled(False)
        self.cancel_button = QPushButton("Dừng tác vụ", self)
        self.cancel_button.setObjectName("cancelButton")
        self.cancel_button.setAccessibleName("Dừng tác vụ hiện tại")
        self.cancel_button.setMinimumHeight(48)
        self.cancel_button.setEnabled(False)
        self.cancel_button.hide()
        self.status_label = QLabel("●  Chưa có audio", self)
        self.status_label.setObjectName("statusLabel")
        self.status_label.setProperty("state", "neutral")
        self.status_label.setWordWrap(False)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 8, 0, 0)
        actions.setSpacing(8)
        actions.addStretch()
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.synthesize_button)

        self._composer_card = QFrame(self)
        self._composer_card.setObjectName("composerCard")
        self._composer_layout = QVBoxLayout(self._composer_card)
        self._composer_layout.setContentsMargins(24, 22, 24, 24)
        self._composer_layout.setSpacing(18)
        self._composer_layout.addWidget(self.text_input)
        self._composer_layout.addLayout(actions)

        self._settings_container = QWidget(self)
        self._settings_container.setObjectName("settingsContainer")
        self._settings_layout = QBoxLayout(QBoxLayout.Direction.TopToBottom)
        self._settings_layout.setContentsMargins(0, 0, 0, 0)
        self._settings_layout.setSpacing(16)
        self._settings_layout.addWidget(self.engine_selector)
        self._settings_layout.addWidget(self.voice_selector)
        self._settings_layout.addWidget(self.voice_style)
        self._settings_layout.addStretch()
        self._settings_container.setLayout(self._settings_layout)

        self._workspace_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._workspace_layout.setContentsMargins(0, 0, 0, 0)
        self._workspace_layout.setSpacing(16)
        self._workspace_layout.addWidget(self._composer_card, 2)
        self._workspace_layout.addWidget(self._settings_container, 1)

        eyebrow = QLabel("OFFLINE  ·  TIẾNG VIỆT", self)
        eyebrow.setObjectName("eyebrow")
        app_title = QLabel("GPHI TTS Studio", self)
        app_title.setObjectName("appTitle")
        app_subtitle = QLabel(
            "Chuyển văn bản tiếng Việt thành giọng nói ngay trên thiết bị với một trải nghiệm rõ ràng hơn.",
            self,
        )
        app_subtitle.setObjectName("appSubtitle")
        self._engine_badge = QLabel("Offline · v3", self)
        self._engine_badge.setObjectName("engineBadge")
        self._engine_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._engine_badge.setProperty("state", "success")
        title_column = QVBoxLayout()
        title_column.setContentsMargins(0, 0, 0, 0)
        title_column.setSpacing(3)
        title_column.addWidget(eyebrow)
        title_column.addWidget(app_title)
        title_column.addWidget(app_subtitle)
        self._header_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._header_layout.setContentsMargins(0, 0, 0, 0)
        self._header_layout.addLayout(title_column)
        self._header_layout.addStretch()
        self._header_layout.addWidget(self._engine_badge)

        self._player_card = QFrame(self)
        self._player_card.setObjectName("playerCard")
        self._player_card.setMinimumHeight(190)
        player_title = QLabel("Bản nghe thử", self)
        player_title.setObjectName("playerTitle")
        self._player_header = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._player_header.setContentsMargins(0, 0, 0, 0)
        self._player_header.addWidget(player_title)
        self._player_header.addStretch()
        self._player_header.addWidget(self.status_label)
        self._player_layout = QVBoxLayout(self._player_card)
        self._player_layout.setContentsMargins(38, 28, 38, 26)
        self._player_layout.setSpacing(20)
        self._player_layout.addLayout(self._player_header)
        self._player_body = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._player_body.setContentsMargins(0, 0, 0, 0)
        self._player_body.setSpacing(20)
        self._player_body.addWidget(self.playback_controls)
        self._player_body.addWidget(self.waveform, 1)
        self._player_layout.addLayout(self._player_body)
        self._player_hint = QLabel(
            "Bấm hoặc kéo trên dải sóng để tua đến vị trí bất kỳ.",
            self,
        )
        self._player_hint.setObjectName("playerHint")
        self._player_layout.addWidget(self._player_hint)

        self._header_divider = QFrame(self)
        self._header_divider.setObjectName("sectionDivider")
        self._header_divider.setFrameShape(QFrame.Shape.HLine)
        self._header_divider.setFrameShadow(QFrame.Shadow.Plain)

        self._root_layout = QVBoxLayout()
        self._root_layout.setContentsMargins(28, 26, 28, 24)
        self._root_layout.setSpacing(18)
        self._root_layout.addLayout(self._header_layout)
        self._root_layout.addWidget(self._header_divider)
        self._root_layout.addLayout(self._workspace_layout, 1)
        self._root_layout.addWidget(self._player_card)
        self._content = QWidget(self)
        self._content.setObjectName("appSurface")
        self._content.setLayout(self._root_layout)
        self._scroll_area = QScrollArea(self)
        self._scroll_area.setObjectName("contentScrollArea")
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll_area.setWidget(self._content)
        self.setCentralWidget(self._scroll_area)

        self._connect_signals()
        self._load_style()
        self._apply_responsive_layout(self.width())
        self.engine_selector.set_engines(view_model.engine_infos, settings.tts.default_engine)
        self.engine_selector.set_recommendation(view_model.recommendation)
        self._view_model.initialize()

    @property
    def responsive_mode(self) -> str:
        """Return the active width breakpoint for diagnostics and tests."""

        return self._responsive_mode

    def _apply_responsive_layout(self, width: int) -> None:
        if width >= 960:
            mode = "wide"
        elif width >= 720:
            mode = "compact"
        else:
            mode = "narrow"
        if mode == self._responsive_mode:
            return
        self._responsive_mode = mode

        if mode == "wide":
            self._workspace_layout.setDirection(QBoxLayout.Direction.LeftToRight)
            self._settings_layout.setDirection(QBoxLayout.Direction.TopToBottom)
            self._header_layout.setDirection(QBoxLayout.Direction.LeftToRight)
            self._player_header.setDirection(QBoxLayout.Direction.LeftToRight)
            self._root_layout.setContentsMargins(24, 24, 24, 24)
            self._composer_layout.setContentsMargins(24, 24, 24, 24)
            self._player_layout.setContentsMargins(38, 28, 38, 26)
            self._header_layout.setSpacing(16)
            self._player_body.setDirection(QBoxLayout.Direction.LeftToRight)
            self._workspace_layout.setStretch(0, 2)
            self._workspace_layout.setStretch(1, 1)
            self._settings_layout.setStretch(0, 0)
            self._settings_layout.setStretch(1, 0)
            self._settings_layout.setStretch(2, 0)
            self.text_input.editor.setMinimumHeight(280)
            self.waveform.setMinimumHeight(52)
            self.status_label.setMaximumWidth(480)
            return

        self._workspace_layout.setDirection(QBoxLayout.Direction.TopToBottom)
        self._workspace_layout.setStretch(0, 0)
        self._workspace_layout.setStretch(1, 0)
        self._root_layout.setContentsMargins(16, 16, 16, 16)
        self._composer_layout.setContentsMargins(16, 16, 16, 16)
        self._player_layout.setContentsMargins(24, 22, 24, 22)
        self._header_layout.setSpacing(12)
        self.text_input.editor.setMinimumHeight(220 if mode == "compact" else 200)
        self.waveform.setMinimumHeight(52)

        if mode == "compact":
            self._settings_layout.setDirection(QBoxLayout.Direction.LeftToRight)
            self._settings_layout.setStretch(0, 1)
            self._settings_layout.setStretch(1, 1)
            self._settings_layout.setStretch(2, 1)
            self._header_layout.setDirection(QBoxLayout.Direction.LeftToRight)
            self._player_header.setDirection(QBoxLayout.Direction.LeftToRight)
            self._player_body.setDirection(QBoxLayout.Direction.LeftToRight)
            self.status_label.setMaximumWidth(400)
            return

        self._settings_layout.setDirection(QBoxLayout.Direction.TopToBottom)
        self._settings_layout.setStretch(0, 0)
        self._settings_layout.setStretch(1, 0)
        self._settings_layout.setStretch(2, 0)
        self._header_layout.setDirection(QBoxLayout.Direction.TopToBottom)
        self._player_header.setDirection(QBoxLayout.Direction.TopToBottom)
        self._player_body.setDirection(QBoxLayout.Direction.TopToBottom)
        self.status_label.setMaximumWidth(16_777_215)

    def _connect_signals(self) -> None:
        self.text_input.text_changed.connect(lambda _text: self._refresh_actions())
        self.text_input.open_file_requested.connect(self._choose_document)
        self.engine_selector.engine_changed.connect(self._view_model.select_engine)
        self.synthesize_button.clicked.connect(self._request_synthesis)
        self.cancel_button.clicked.connect(self._view_model.cancel_current_task)
        self._view_model.voices_changed.connect(self._voices_changed)
        self._view_model.capabilities_changed.connect(self._capabilities_changed)
        self._view_model.state_changed.connect(self._state_changed)
        self._view_model.error_occurred.connect(self._show_error)
        self._view_model.synthesis_completed.connect(self._synthesis_completed)
        self._view_model.document_imported.connect(self._document_imported)
        self.playback_controls.play_requested.connect(self._play)
        self.playback_controls.pause_requested.connect(self._playback.pause)
        self.playback_controls.stop_requested.connect(self._playback.stop)
        self.waveform.seek_requested.connect(self._playback.seek)
        self._playback.state_changed.connect(self._playback_state_changed)
        self._playback.position_changed.connect(self.waveform.set_position)
        self._playback.error_occurred.connect(self._show_playback_error)

    def _load_style(self) -> None:
        self.setStyleSheet(build_stylesheet())

    def _request_synthesis(self) -> None:
        self._playback.clear()
        self.waveform.clear()
        self._view_model.synthesize(
            self.text_input.text(),
            self.voice_style.effects(),
            self.voice_selector.current_voice_id(),
            self.voice_style.current_style_id(),
        )

    def _choose_document(self) -> None:
        source_path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Mở tài liệu",
            "",
            "Tài liệu hỗ trợ (*.txt *.srt *.docx *.pdf);;Văn bản (*.txt);;"
            "Phụ đề (*.srt);;Word (*.docx);;PDF (*.pdf)",
        )
        if source_path:
            self._view_model.import_document(source_path)

    def _document_imported(self, document: ImportedDocument) -> None:
        text = document.text
        display_name = document.display_name
        self.text_input.set_text(text)
        formatted_count = f"{len(text):,}".replace(",", ".")
        self.status_label.setText(
            f"●  Đã nhập '{display_name}' ({formatted_count} ký tự)."
        )
        self._set_status_style("success")
        self.text_input.editor.setFocus()
        self._refresh_actions()

    def _voices_changed(self, voices: list) -> None:
        self.voice_selector.set_voices(voices)
        self._refresh_actions()

    def _capabilities_changed(self, capabilities: object) -> None:
        style_ids = tuple(getattr(capabilities, "supported_style_ids", ("tu_nhien",)))
        self.voice_style.set_supported_styles(style_ids)

    def _state_changed(self, state: str) -> None:
        messages = {
            "idle": "Engine đã sẵn sàng.",
            "loading_engine": "Đang tải engine...",
            "importing_document": "Đang đọc và trích xuất văn bản từ tệp...",
            "synthesizing": "Đang tạo giọng nói...",
            "completed": "Tạo giọng nói hoàn tất.",
            "error": "Không thể hoàn thành tác vụ.",
            "cancelled": "Tác vụ đã được hủy.",
        }
        self.status_label.setText(f"●  {messages[state]}")
        status_style = {
            "idle": "success",
            "loading_engine": "busy",
            "importing_document": "busy",
            "synthesizing": "busy",
            "completed": "success",
            "error": "error",
            "cancelled": "warning",
        }
        self._set_status_style(status_style[state])
        engine_status = {
            "idle": ("Sẵn sàng", "success"),
            "loading_engine": ("Đang tải", "busy"),
            "importing_document": ("Đang nhập tệp", "busy"),
            "synthesizing": ("Đang xử lý", "busy"),
            "completed": ("Sẵn sàng", "success"),
            "error": ("Có lỗi", "error"),
            "cancelled": ("Đã dừng", "neutral"),
        }
        self.engine_selector.set_status(*engine_status[state])
        busy = state in {"loading_engine", "importing_document", "synthesizing"}
        self.cancel_button.setEnabled(busy)
        self.cancel_button.setVisible(busy)
        self.engine_selector.combo.setEnabled(not busy)
        self.text_input.open_file_button.setEnabled(not busy)
        self.text_input.editor.setReadOnly(state == "importing_document")
        self._refresh_actions()

    def _show_error(self, message: str) -> None:
        self.status_label.setText(f"●  Lỗi: {message}")
        self._set_status_style("error")
        self._refresh_actions()

    def _synthesis_completed(self, result: SynthesisResult) -> None:
        duration = result.audio.size / result.sample_rate
        try:
            self._playback.set_audio(result)
        except PlaybackError as exc:
            self._show_playback_error(str(exc))
            return
        self.waveform.set_result(result)
        self.status_label.setText(f"●  Hoàn tất · Audio {duration:.2f} giây")
        self._set_status_style("success")
        self._refresh_actions()

    def _play(self) -> None:
        try:
            self._playback.play()
        except PlaybackError as exc:
            self._show_playback_error(str(exc))

    def _playback_state_changed(self, state: str) -> None:
        self.playback_controls.set_playback_state(state)
        messages = {
            "playing": "Đang phát audio...",
            "paused": "Đã tạm dừng audio.",
            "stopped": "Đã dừng audio.",
        }
        if state in messages:
            self.status_label.setText(f"●  {messages[state]}")
            self._set_status_style("busy" if state == "playing" else "neutral")

    def _show_playback_error(self, message: str) -> None:
        self.status_label.setText(f"●  Lỗi playback: {message}")
        self._set_status_style("error")
        self.playback_controls.set_playback_state(self._playback.state)

    def _set_status_style(self, state: str) -> None:
        self.status_label.setProperty("state", state)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _refresh_actions(self) -> None:
        ready = (
            bool(self.text_input.text().strip())
            and self.voice_selector.current_voice_id() is not None
            and self._view_model.state
            not in {"loading_engine", "importing_document", "synthesizing"}
        )
        self.synthesize_button.setEnabled(ready)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Reflow cards when the window crosses a responsive breakpoint."""

        super().resizeEvent(event)
        if hasattr(self, "_workspace_layout"):
            self._apply_responsive_layout(event.size().width())

    def closeEvent(self, event: QCloseEvent) -> None:
        """Release worker and engine resources before closing."""

        self._playback.shutdown()
        self._view_model.shutdown()
        super().closeEvent(event)
