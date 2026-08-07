"""Minimal runnable desktop window for the current TTS workflow."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QResizeEvent
from PySide6.QtWidgets import (
    QBoxLayout,
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
from vntts.db.models import SynthesisResult
from vntts.services.playback import PlaybackService
from vntts.utils.exceptions import PlaybackError
from vntts.ui.compose_view import (
    EngineSelector,
    MainViewModel,
    PlaybackControls,
    TextInputWidget,
    WaveformPreview,
)
from vntts.ui.settings_panel import VoiceSettingsWidget


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
        self.setObjectName("mainWindow")
        self.setWindowTitle(settings.application.name)
        self.resize(1080, 760)
        self.setMinimumSize(640, 560)
        self._responsive_mode = ""

        self.text_input = TextInputWidget(settings.tts.max_text_length, self)
        self.engine_selector = EngineSelector(self)
        self.voice_settings = VoiceSettingsWidget(settings.audio, self)
        self.playback_controls = PlaybackControls(self)
        self.waveform = WaveformPreview(self)
        self.synthesize_button = QPushButton("Tạo giọng nói", self)
        self.synthesize_button.setObjectName("synthesizeButton")
        self.synthesize_button.setAccessibleName("Tạo giọng nói")
        self.synthesize_button.setMinimumSize(176, 48)
        self.synthesize_button.setEnabled(False)
        self.cancel_button = QPushButton("Hủy", self)
        self.cancel_button.setObjectName("cancelButton")
        self.cancel_button.setAccessibleName("Hủy tác vụ hiện tại")
        self.cancel_button.setMinimumHeight(48)
        self.cancel_button.setEnabled(False)
        self.status_label = QLabel("Sẵn sàng", self)
        self.status_label.setObjectName("statusLabel")
        self.status_label.setProperty("state", "neutral")
        self.status_label.setWordWrap(True)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 8, 0, 0)
        actions.setSpacing(8)
        actions.addStretch()
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.synthesize_button)

        self._composer_card = QFrame(self)
        self._composer_card.setObjectName("composerCard")
        self._composer_layout = QVBoxLayout(self._composer_card)
        self._composer_layout.setContentsMargins(24, 24, 24, 24)
        self._composer_layout.setSpacing(16)
        self._composer_layout.addWidget(self.text_input)
        self._composer_layout.addLayout(actions)

        self._settings_container = QWidget(self)
        self._settings_container.setObjectName("settingsContainer")
        self._settings_layout = QBoxLayout(QBoxLayout.Direction.TopToBottom)
        self._settings_layout.setContentsMargins(0, 0, 0, 0)
        self._settings_layout.setSpacing(16)
        self._settings_layout.addWidget(self.engine_selector)
        self._settings_layout.addWidget(self.voice_settings)
        self._settings_layout.addStretch()
        self._settings_container.setLayout(self._settings_layout)

        self._workspace_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._workspace_layout.setContentsMargins(0, 0, 0, 0)
        self._workspace_layout.setSpacing(16)
        self._workspace_layout.addWidget(self._composer_card, 2)
        self._workspace_layout.addWidget(self._settings_container, 1)

        app_title = QLabel("Vietnamese TTS Studio", self)
        app_title.setObjectName("appTitle")
        app_subtitle = QLabel(
            "Chuyển văn bản tiếng Việt thành giọng nói ngay trên thiết bị.",
            self,
        )
        app_subtitle.setObjectName("appSubtitle")
        title_column = QVBoxLayout()
        title_column.setContentsMargins(0, 0, 0, 0)
        title_column.setSpacing(0)
        title_column.addWidget(app_title)
        title_column.addWidget(app_subtitle)
        self._engine_badge = QLabel("VieNeu v3 · Local", self)
        self._engine_badge.setObjectName("engineBadge")
        self._engine_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._header_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._header_layout.setContentsMargins(0, 0, 0, 0)
        self._header_layout.addLayout(title_column)
        self._header_layout.addStretch()
        self._header_layout.addWidget(self._engine_badge)

        self._player_card = QFrame(self)
        self._player_card.setObjectName("playerCard")
        player_title = QLabel("Bản xem trước", self)
        player_title.setObjectName("sectionTitle")
        self._player_header = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._player_header.setContentsMargins(0, 0, 0, 0)
        self._player_header.addWidget(player_title)
        self._player_header.addStretch()
        self._player_header.addWidget(self.status_label)
        self._player_layout = QVBoxLayout(self._player_card)
        self._player_layout.setContentsMargins(24, 16, 24, 16)
        self._player_layout.setSpacing(8)
        self._player_layout.addLayout(self._player_header)
        self._player_layout.addWidget(self.waveform)
        self._player_layout.addWidget(self.playback_controls)

        self._root_layout = QVBoxLayout()
        self._root_layout.setContentsMargins(24, 24, 24, 24)
        self._root_layout.setSpacing(16)
        self._root_layout.addLayout(self._header_layout)
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
            self._workspace_layout.setStretch(0, 2)
            self._workspace_layout.setStretch(1, 1)
            self._settings_layout.setStretch(0, 0)
            self._settings_layout.setStretch(1, 0)
            self.text_input.editor.setMinimumHeight(280)
            self.waveform.setMinimumHeight(88)
            self.status_label.setMaximumWidth(480)
            self._header_layout.setAlignment(
                self._engine_badge, Qt.AlignmentFlag.AlignRight
            )
            return

        self._workspace_layout.setDirection(QBoxLayout.Direction.TopToBottom)
        self._workspace_layout.setStretch(0, 0)
        self._workspace_layout.setStretch(1, 0)
        self._root_layout.setContentsMargins(16, 16, 16, 16)
        self._composer_layout.setContentsMargins(16, 16, 16, 16)
        self.text_input.editor.setMinimumHeight(220 if mode == "compact" else 200)
        self.waveform.setMinimumHeight(80 if mode == "compact" else 72)

        if mode == "compact":
            self._settings_layout.setDirection(QBoxLayout.Direction.LeftToRight)
            self._settings_layout.setStretch(0, 1)
            self._settings_layout.setStretch(1, 1)
            self._header_layout.setDirection(QBoxLayout.Direction.LeftToRight)
            self._player_header.setDirection(QBoxLayout.Direction.LeftToRight)
            self.status_label.setMaximumWidth(400)
            self._header_layout.setAlignment(
                self._engine_badge, Qt.AlignmentFlag.AlignRight
            )
            return

        self._settings_layout.setDirection(QBoxLayout.Direction.TopToBottom)
        self._settings_layout.setStretch(0, 0)
        self._settings_layout.setStretch(1, 0)
        self._header_layout.setDirection(QBoxLayout.Direction.TopToBottom)
        self._player_header.setDirection(QBoxLayout.Direction.TopToBottom)
        self.status_label.setMaximumWidth(16_777_215)
        self._header_layout.setAlignment(
            self._engine_badge, Qt.AlignmentFlag.AlignLeft
        )

    def _connect_signals(self) -> None:
        self.text_input.text_changed.connect(lambda _text: self._refresh_actions())
        self.engine_selector.engine_changed.connect(self._view_model.select_engine)
        self.synthesize_button.clicked.connect(self._request_synthesis)
        self.cancel_button.clicked.connect(self._view_model.cancel_current_task)
        self._view_model.voices_changed.connect(self._voices_changed)
        self._view_model.state_changed.connect(self._state_changed)
        self._view_model.error_occurred.connect(self._show_error)
        self._view_model.synthesis_completed.connect(self._synthesis_completed)
        self.playback_controls.play_requested.connect(self._play)
        self.playback_controls.pause_requested.connect(self._playback.pause)
        self.playback_controls.stop_requested.connect(self._playback.stop)
        self._playback.state_changed.connect(self._playback_state_changed)
        self._playback.error_occurred.connect(self._show_playback_error)

    def _load_style(self) -> None:
        style_path = Path(__file__).parent / "resources" / "styles.qss"
        try:
            self.setStyleSheet(style_path.read_text(encoding="utf-8"))
        except OSError:
            self.setStyleSheet("")

    def _request_synthesis(self) -> None:
        self._playback.clear()
        self.waveform.clear()
        self._view_model.synthesize(
            self.text_input.text(),
            self.voice_settings.effects(),
            self.voice_settings.current_voice_id(),
        )

    def _voices_changed(self, voices: list) -> None:
        self.voice_settings.set_voices(voices)
        self._refresh_actions()

    def _state_changed(self, state: str) -> None:
        messages = {
            "idle": "Engine đã sẵn sàng.",
            "loading_engine": "Đang tải engine...",
            "synthesizing": "Đang tổng hợp bằng worker nền...",
            "completed": "Tổng hợp hoàn tất.",
            "error": "Không thể hoàn thành tác vụ.",
            "cancelled": "Tác vụ đã được hủy.",
        }
        self.status_label.setText(messages[state])
        status_style = {
            "idle": "success",
            "loading_engine": "busy",
            "synthesizing": "busy",
            "completed": "success",
            "error": "error",
            "cancelled": "warning",
        }
        self._set_status_style(status_style[state])
        busy = state in {"loading_engine", "synthesizing"}
        self.cancel_button.setEnabled(busy)
        self.engine_selector.combo.setEnabled(not busy)
        self._refresh_actions()

    def _show_error(self, message: str) -> None:
        self.status_label.setText(f"Lỗi: {message}")
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
        self.status_label.setText(f"Hoàn tất audio ({duration:.2f} giây). Sẵn sàng phát.")
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
            self.status_label.setText(messages[state])
            self._set_status_style("busy" if state == "playing" else "neutral")

    def _show_playback_error(self, message: str) -> None:
        self.status_label.setText(f"Lỗi playback: {message}")
        self._set_status_style("error")
        self.playback_controls.set_playback_state(self._playback.state)

    def _set_status_style(self, state: str) -> None:
        self.status_label.setProperty("state", state)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _refresh_actions(self) -> None:
        ready = (
            bool(self.text_input.text().strip())
            and self.voice_settings.current_voice_id() is not None
            and self._view_model.state not in {"loading_engine", "synthesizing"}
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
