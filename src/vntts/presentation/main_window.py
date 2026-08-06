"""Minimal runnable desktop window for the Phase 1 workflow."""

from pathlib import Path

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from vntts.config.settings import Settings
from vntts.domain.tts.models import SynthesisResult
from vntts.presentation.viewmodels.main_viewmodel import MainViewModel
from vntts.presentation.widgets.engine_selector import EngineSelector
from vntts.presentation.widgets.playback_controls import PlaybackControls
from vntts.presentation.widgets.text_input_widget import TextInputWidget
from vntts.presentation.widgets.voice_settings_widget import VoiceSettingsWidget


class MainWindow(QMainWindow):
    """Compose widgets and reflect state emitted by MainViewModel."""

    def __init__(self, view_model: MainViewModel, settings: Settings) -> None:
        super().__init__()
        self._view_model = view_model
        self._settings = settings
        self.setObjectName("mainWindow")
        self.setWindowTitle(settings.application.name)
        self.resize(820, 680)

        self.text_input = TextInputWidget(settings.tts.max_text_length, self)
        self.engine_selector = EngineSelector(self)
        self.voice_settings = VoiceSettingsWidget(settings.audio, self)
        self.playback_controls = PlaybackControls(self)
        self.synthesize_button = QPushButton("Tổng hợp", self)
        self.synthesize_button.setObjectName("synthesizeButton")
        self.synthesize_button.setEnabled(False)
        self.cancel_button = QPushButton("Hủy", self)
        self.cancel_button.setObjectName("cancelButton")
        self.cancel_button.setEnabled(False)
        self.status_label = QLabel("Sẵn sàng", self)
        self.status_label.setObjectName("statusLabel")
        self.status_label.setWordWrap(True)

        actions = QHBoxLayout()
        actions.addWidget(self.synthesize_button)
        actions.addWidget(self.cancel_button)
        root = QVBoxLayout()
        root.addWidget(self.text_input)
        root.addWidget(self.engine_selector)
        root.addWidget(self.voice_settings)
        root.addLayout(actions)
        root.addWidget(self.playback_controls)
        root.addWidget(self.status_label)
        container = QWidget(self)
        container.setLayout(root)
        self.setCentralWidget(container)

        self._connect_signals()
        self._load_style()
        self.engine_selector.set_engines(view_model.engine_infos, settings.tts.default_engine)
        self.engine_selector.set_recommendation(view_model.recommendation)
        self._view_model.initialize()

    def _connect_signals(self) -> None:
        self.text_input.text_changed.connect(lambda _text: self._refresh_actions())
        self.engine_selector.engine_changed.connect(self._view_model.select_engine)
        self.synthesize_button.clicked.connect(self._request_synthesis)
        self.cancel_button.clicked.connect(self._view_model.cancel_current_task)
        self._view_model.voices_changed.connect(self._voices_changed)
        self._view_model.state_changed.connect(self._state_changed)
        self._view_model.error_occurred.connect(self._show_error)
        self._view_model.synthesis_completed.connect(self._synthesis_completed)

    def _load_style(self) -> None:
        style_path = Path(__file__).parent / "resources" / "styles.qss"
        try:
            self.setStyleSheet(style_path.read_text(encoding="utf-8"))
        except OSError:
            self.setStyleSheet("")

    def _request_synthesis(self) -> None:
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
        busy = state in {"loading_engine", "synthesizing"}
        self.cancel_button.setEnabled(busy)
        self.engine_selector.combo.setEnabled(not busy)
        self._refresh_actions()

    def _show_error(self, message: str) -> None:
        self.status_label.setText(f"Lỗi: {message}")
        self._refresh_actions()

    def _synthesis_completed(self, result: SynthesisResult) -> None:
        duration = result.audio.size / result.sample_rate
        self.status_label.setText(
            f"Hoàn tất audio giả ({duration:.2f} giây). Playback chưa được triển khai."
        )
        self._refresh_actions()

    def _refresh_actions(self) -> None:
        ready = (
            bool(self.text_input.text().strip())
            and self.voice_settings.current_voice_id() is not None
            and self._view_model.state not in {"loading_engine", "synthesizing"}
        )
        self.synthesize_button.setEnabled(ready)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Release worker and fake-engine resources before closing."""

        self._view_model.shutdown()
        super().closeEvent(event)
