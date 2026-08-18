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
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from vntts.config.settings import Settings
from vntts.config.theme import THEME, get_system_font
from vntts.db.models import (
    VIENEU_V3_ENGINE_ID,
    AudioEffects,
    SynthesisResult,
    VoiceInfo,
)
from vntts.services.document_import import ImportedDocument
from vntts.services.playback import PlaybackService
from vntts.services.voice_profiles import VoiceProfileStore
from vntts.ui.compose_view import (
    MainViewModel,
    PlaybackControls,
    TextInputWidget,
    WaveformPreview,
)
from vntts.ui.contact_panel import ContactPage
from vntts.ui.settings_panel import (
    ActiveModelCard,
    ModelSettingsPage,
    VoiceSelectorWidget,
    VoiceStyleWidget,
)
from vntts.ui.voice_clone_view import VoiceClonePage
from vntts.utils.exceptions import PlaybackError


class MainWindow(QMainWindow):
    """Compose widgets and reflect state emitted by MainViewModel."""

    def __init__(
        self,
        view_model: MainViewModel,
        settings: Settings,
        playback: PlaybackService | None = None,
        voice_profile_store: VoiceProfileStore | None = None,
    ) -> None:
        super().__init__()
        self._view_model = view_model
        self._settings = settings
        self._playback = playback or PlaybackService(self)
        self._clone_playback = PlaybackService(self)
        self._voice_profile_store = voice_profile_store or VoiceProfileStore(
            settings.paths.data_dir
        )
        self._engine_voices: list[VoiceInfo] = []
        self._cloned_voice_artifacts: dict[str, str] = {}
        self._clone_enrollment_pending = False
        self._clone_preview_pending = False
        self._clone_preview_active = False
        self.setObjectName("AppRoot")
        self.setWindowTitle(settings.application.name)
        self.resize(1180, 760)
        self.setMinimumSize(760, 600)
        self.setFont(get_system_font())
        self._responsive_mode = ""

        self.text_input = TextInputWidget(self)
        self.active_model_card = ActiveModelCard(self)
        self.voice_selector = VoiceSelectorWidget(self)
        self.voice_style = VoiceStyleWidget(settings.audio, self)
        self.playback_controls = PlaybackControls(self)
        self.waveform = WaveformPreview(self)
        self.export_wav_button = QPushButton("Xuất WAV", self)
        self.export_wav_button.setObjectName("exportWavButton")
        self.export_wav_button.setProperty("variant", "secondary")
        self.export_wav_button.setAccessibleName("Xuất audio WAV")
        self.export_wav_button.setEnabled(False)
        self.export_mp3_button = QPushButton("Xuất MP3", self)
        self.export_mp3_button.setObjectName("exportMp3Button")
        self.export_mp3_button.setProperty("variant", "secondary")
        self.export_mp3_button.setAccessibleName("Xuất audio MP3")
        self.export_mp3_button.setEnabled(False)
        self.synthesize_button = QPushButton("Tạo giọng nói", self)
        self.synthesize_button.setObjectName("synthesizeButton")
        self.synthesize_button.setProperty("variant", "primary")
        self.synthesize_button.setAccessibleName("Tạo giọng nói")
        self.synthesize_button.setMinimumSize(176, 48)
        self.synthesize_button.setEnabled(False)
        self.cancel_button = QPushButton("Dừng tác vụ", self)
        self.cancel_button.setObjectName("cancelButton")
        self.cancel_button.setProperty("variant", "secondary")
        self.cancel_button.setAccessibleName("Dừng tác vụ hiện tại")
        self.cancel_button.setMinimumHeight(48)
        self.cancel_button.setEnabled(False)
        self.cancel_button.hide()
        self.status_label = QLabel("●  Chưa có audio", self)
        self.status_label.setObjectName("statusLabel")
        self.status_label.setProperty("state", "neutral")
        self.status_label.setWordWrap(False)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, THEME.space_2, 0, 0)
        actions.setSpacing(THEME.space_2)
        actions.addStretch()
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.synthesize_button)

        self._composer_card = QFrame(self)
        self._composer_card.setObjectName("composerCard")
        self._composer_card.setProperty("card", True)
        self._composer_layout = QVBoxLayout(self._composer_card)
        self._composer_layout.setContentsMargins(
            THEME.space_4,
            THEME.space_4,
            THEME.space_4,
            THEME.space_4,
        )
        self._composer_layout.setSpacing(THEME.space_3)
        self._composer_layout.addWidget(self.text_input)
        self._composer_layout.addLayout(actions)

        self._settings_container = QWidget(self)
        self._settings_container.setObjectName("settingsContainer")
        self._settings_layout = QBoxLayout(QBoxLayout.Direction.TopToBottom)
        self._settings_layout.setContentsMargins(0, 0, 0, 0)
        # QGroupBox reserves THEME.space_3 above its border for the title,
        # which also creates the visual gap shown between the stacked cards.
        self._settings_layout.setSpacing(0)
        self._settings_layout.addWidget(self.active_model_card)
        self._settings_layout.addWidget(self.voice_selector)
        self._settings_layout.addWidget(self.voice_style)
        self._settings_layout.addStretch()
        self._settings_container.setLayout(self._settings_layout)

        self._workspace_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._workspace_layout.setContentsMargins(0, 0, 0, 0)
        self._workspace_layout.setSpacing(THEME.space_3)
        self._workspace_layout.addWidget(self._composer_card, 2)
        self._workspace_layout.addWidget(self._settings_container, 1)

        app_title = QLabel("Tạo giọng nói", self)
        app_title.setProperty("role", "title")
        self._toolbar = QFrame(self)
        self._toolbar.setObjectName("toolbar")
        self._toolbar.setFixedHeight(THEME.toolbar_height)
        self._header_layout = QBoxLayout(
            QBoxLayout.Direction.LeftToRight,
            self._toolbar,
        )
        self._header_layout.setContentsMargins(THEME.space_4, 0, THEME.space_4, 0)
        self._header_layout.addWidget(app_title)
        self._header_layout.addStretch()

        self._player_card = QFrame(self)
        self._player_card.setObjectName("playerCard")
        self._player_card.setProperty("card", True)
        self._player_card.setMinimumHeight(136)
        player_title = QLabel("Bản nghe thử", self)
        player_title.setObjectName("playerTitle")
        player_title.setProperty("role", "section")
        self._player_header = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._player_header.setContentsMargins(0, 0, 0, 0)
        self._player_header.addWidget(player_title)
        self._player_header.addStretch()
        self._player_header.addWidget(self.export_wav_button)
        self._player_header.addWidget(self.export_mp3_button)
        self._player_header.addWidget(self.status_label)
        self._player_layout = QVBoxLayout(self._player_card)
        self._player_layout.setContentsMargins(
            THEME.space_4,
            THEME.space_3,
            THEME.space_4,
            THEME.space_3,
        )
        self._player_layout.setSpacing(THEME.space_2)
        self._player_layout.addLayout(self._player_header)
        self._player_body = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._player_body.setContentsMargins(0, 0, 0, 0)
        self._player_body.setSpacing(THEME.space_3)
        self._player_body.addWidget(self.playback_controls)
        self._player_body.addWidget(self.waveform, 1)
        self._player_layout.addLayout(self._player_body)
        self._player_hint = QLabel(
            "Bấm hoặc kéo trên dải sóng để tua đến vị trí bất kỳ.",
            self,
        )
        self._player_hint.setObjectName("playerHint")
        self._player_hint.setProperty("role", "caption")
        self._player_hint.hide()

        self._header_divider = QFrame(self)
        self._header_divider.setObjectName("sectionDivider")
        self._header_divider.setFrameShape(QFrame.Shape.HLine)
        self._header_divider.setFrameShadow(QFrame.Shadow.Plain)

        self._root_layout = QVBoxLayout()
        self._root_layout.setContentsMargins(
            THEME.space_4,
            THEME.space_3,
            THEME.space_4,
            THEME.space_4,
        )
        self._root_layout.setSpacing(THEME.space_3)
        self._root_layout.addWidget(self._toolbar)
        self._root_layout.addLayout(self._workspace_layout, 1)
        self._root_layout.addWidget(self._player_card)
        self._content = QWidget(self)
        self._content.setObjectName("content")
        self._content.setLayout(self._root_layout)
        self._scroll_area = QScrollArea(self)
        self._scroll_area.setObjectName("contentScrollArea")
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll_area.setWidget(self._content)

        self.voice_clone_page = VoiceClonePage(self._voice_profile_store, self)
        self._clone_scroll_area = QScrollArea(self)
        self._clone_scroll_area.setObjectName("voiceCloneScrollArea")
        self._clone_scroll_area.setWidgetResizable(True)
        self._clone_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._clone_scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._clone_scroll_area.setWidget(self.voice_clone_page)
        self.model_settings_page = ModelSettingsPage(self)
        self._model_settings_scroll_area = QScrollArea(self)
        self._model_settings_scroll_area.setObjectName("modelSettingsScrollArea")
        self._model_settings_scroll_area.setWidgetResizable(True)
        self._model_settings_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._model_settings_scroll_area.setWidget(self.model_settings_page)
        self.contact_page = ContactPage(self)
        self._contact_scroll_area = QScrollArea(self)
        self._contact_scroll_area.setObjectName("contactScrollArea")
        self._contact_scroll_area.setWidgetResizable(True)
        self._contact_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._contact_scroll_area.setWidget(self.contact_page)
        self.page_stack = QStackedWidget(self)
        self.page_stack.setObjectName("pageStack")
        self.page_stack.addWidget(self._scroll_area)
        self.page_stack.addWidget(self._clone_scroll_area)
        self.page_stack.addWidget(self._model_settings_scroll_area)
        self.page_stack.addWidget(self._contact_scroll_area)

        self._sidebar = QFrame(self)
        self._sidebar.setObjectName("sidebar")
        self._sidebar.setFixedWidth(THEME.sidebar_width)
        brand = QLabel("GPHI TTS", self._sidebar)
        brand.setObjectName("sidebarBrand")
        brand.setProperty("role", "section")
        self.nav_compose_button = QPushButton("Tạo giọng nói", self._sidebar)
        self.nav_compose_button.setObjectName("navComposeButton")
        self.nav_clone_button = QPushButton("Nhân bản giọng", self._sidebar)
        self.nav_clone_button.setObjectName("navCloneButton")
        self.nav_settings_button = QPushButton("Cài đặt", self._sidebar)
        self.nav_settings_button.setObjectName("navSettingsButton")
        self.nav_contact_button = QPushButton("Liên hệ", self._sidebar)
        self.nav_contact_button.setObjectName("navContactButton")
        for button in (
            self.nav_compose_button,
            self.nav_clone_button,
            self.nav_settings_button,
            self.nav_contact_button,
        ):
            button.setCheckable(True)
            button.setProperty("nav", True)
        self.nav_compose_button.setChecked(True)
        sidebar_layout = QVBoxLayout(self._sidebar)
        sidebar_layout.setContentsMargins(
            THEME.space_3,
            THEME.space_5,
            THEME.space_3,
            THEME.space_4,
        )
        sidebar_layout.setSpacing(THEME.space_2)
        sidebar_layout.addWidget(brand)
        sidebar_layout.addSpacing(THEME.space_5)
        sidebar_layout.addWidget(self.nav_compose_button)
        sidebar_layout.addWidget(self.nav_clone_button)
        sidebar_layout.addWidget(self.nav_settings_button)
        sidebar_layout.addWidget(self.nav_contact_button)
        sidebar_layout.addStretch()

        shell = QWidget(self)
        shell.setObjectName("applicationShell")
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        shell_layout.addWidget(self._sidebar)
        shell_layout.addWidget(self.page_stack, 1)
        self.setCentralWidget(shell)

        self._connect_signals()
        self._apply_responsive_layout(self.width() - THEME.sidebar_width)
        self.model_settings_page.set_models(
            view_model.engine_infos,
            settings.tts.default_engine,
        )
        self.model_settings_page.set_hardware(
            view_model.hardware,
            settings.hardware_recommendation.high_tier.min_vram_gb,
        )
        self.contact_page.set_info(
            settings.application.manufacturer,
            settings.application.address,
            settings.application.phone,
            settings.application.support_email,
            settings.application.website,
        )
        self.active_model_card.set_hardware(view_model.hardware)
        self._profiles_changed(self.voice_clone_page.profiles)

    def start_initialization(self) -> None:
        """Start slow startup work after the window has been shown."""

        self._view_model.initialize()

    @property
    def responsive_mode(self) -> str:
        """Return the active width breakpoint for diagnostics and tests."""

        return self._responsive_mode

    def _apply_responsive_layout(self, width: int) -> None:
        if width >= 820:
            mode = "wide"
        elif width >= 600:
            mode = "compact"
        else:
            mode = "narrow"
        if mode == self._responsive_mode:
            return
        self._responsive_mode = mode

        if mode == "wide":
            self._settings_container.setMaximumWidth(320)
            self._workspace_layout.setDirection(QBoxLayout.Direction.LeftToRight)
            self._settings_layout.setDirection(QBoxLayout.Direction.TopToBottom)
            self._header_layout.setDirection(QBoxLayout.Direction.LeftToRight)
            self._player_header.setDirection(QBoxLayout.Direction.LeftToRight)
            self._root_layout.setContentsMargins(
                THEME.space_4,
                THEME.space_3,
                THEME.space_4,
                THEME.space_4,
            )
            self._composer_layout.setContentsMargins(
                THEME.space_4,
                THEME.space_4,
                THEME.space_4,
                THEME.space_4,
            )
            self._player_layout.setContentsMargins(
                THEME.space_4,
                THEME.space_3,
                THEME.space_4,
                THEME.space_3,
            )
            self._header_layout.setSpacing(THEME.space_3)
            self._player_body.setDirection(QBoxLayout.Direction.LeftToRight)
            self._workspace_layout.setStretch(0, 2)
            self._workspace_layout.setStretch(1, 1)
            self._settings_layout.setStretch(0, 0)
            self._settings_layout.setStretch(1, 0)
            self._settings_layout.setStretch(2, 0)
            self._settings_layout.setStretch(3, 1)
            self.text_input.editor.setMinimumHeight(180)
            self.waveform.setMinimumHeight(52)
            self.status_label.setMaximumWidth(360)
            return

        self._workspace_layout.setDirection(QBoxLayout.Direction.TopToBottom)
        self._settings_container.setMaximumWidth(16_777_215)
        self._workspace_layout.setStretch(0, 0)
        self._workspace_layout.setStretch(1, 0)
        self._root_layout.setContentsMargins(
            THEME.space_3,
            THEME.space_2,
            THEME.space_3,
            THEME.space_3,
        )
        self._composer_layout.setContentsMargins(
            THEME.space_3,
            THEME.space_3,
            THEME.space_3,
            THEME.space_3,
        )
        self._player_layout.setContentsMargins(
            THEME.space_3,
            THEME.space_3,
            THEME.space_3,
            THEME.space_3,
        )
        self._header_layout.setSpacing(THEME.space_2)
        self.text_input.editor.setMinimumHeight(170 if mode == "compact" else 160)
        self.waveform.setMinimumHeight(52)

        if mode == "compact":
            self._settings_layout.setDirection(QBoxLayout.Direction.TopToBottom)
            self._settings_layout.setStretch(0, 0)
            self._settings_layout.setStretch(1, 0)
            self._settings_layout.setStretch(2, 0)
            self._settings_layout.setStretch(3, 1)
            self._header_layout.setDirection(QBoxLayout.Direction.LeftToRight)
            self._player_header.setDirection(QBoxLayout.Direction.LeftToRight)
            self._player_body.setDirection(QBoxLayout.Direction.LeftToRight)
            self.status_label.setMaximumWidth(320)
            return

        self._settings_layout.setDirection(QBoxLayout.Direction.TopToBottom)
        self._settings_layout.setStretch(0, 0)
        self._settings_layout.setStretch(1, 0)
        self._settings_layout.setStretch(2, 0)
        self._settings_layout.setStretch(3, 1)
        self._header_layout.setDirection(QBoxLayout.Direction.TopToBottom)
        self._player_header.setDirection(QBoxLayout.Direction.TopToBottom)
        self._player_body.setDirection(QBoxLayout.Direction.TopToBottom)
        self.status_label.setMaximumWidth(16_777_215)

    def _connect_signals(self) -> None:
        self.nav_compose_button.clicked.connect(lambda: self._show_page(0))
        self.nav_clone_button.clicked.connect(lambda: self._show_page(1))
        self.nav_settings_button.clicked.connect(lambda: self._show_page(2))
        self.nav_contact_button.clicked.connect(lambda: self._show_page(3))
        self.voice_clone_page.profiles_changed.connect(self._profiles_changed)
        self.voice_clone_page.enrollment_requested.connect(self._enroll_voice)
        self.voice_clone_page.preview_requested.connect(self._preview_cloned_voice)
        self.voice_clone_page.stop_preview_requested.connect(self._clone_playback.stop)
        self.text_input.text_changed.connect(lambda _text: self._refresh_actions())
        self.text_input.open_file_requested.connect(self._choose_document)
        self.model_settings_page.load_requested.connect(self._view_model.load_model)
        self.synthesize_button.clicked.connect(self._request_synthesis)
        self.cancel_button.clicked.connect(self._view_model.cancel_current_task)
        self._view_model.voices_changed.connect(self._voices_changed)
        self._view_model.capabilities_changed.connect(self._capabilities_changed)
        self._view_model.state_changed.connect(self._state_changed)
        self._view_model.error_occurred.connect(self._show_error)
        self._view_model.synthesis_completed.connect(self._synthesis_completed)
        self._view_model.document_imported.connect(self._document_imported)
        self._view_model.voice_profile_created.connect(self._voice_profile_created)
        self._view_model.runtime_changed.connect(self._runtime_changed)
        self._view_model.hardware_changed.connect(self._hardware_changed)
        self.playback_controls.play_requested.connect(self._play)
        self.playback_controls.pause_requested.connect(self._playback.pause)
        self.playback_controls.stop_requested.connect(self._playback.stop)
        self.export_wav_button.clicked.connect(lambda: self._export_audio("wav"))
        self.export_mp3_button.clicked.connect(lambda: self._export_audio("mp3"))
        self.waveform.seek_requested.connect(self._playback.seek)
        self._playback.state_changed.connect(self._playback_state_changed)
        self._playback.position_changed.connect(self.waveform.set_position)
        self._playback.error_occurred.connect(self._show_playback_error)
        self._clone_playback.state_changed.connect(self._clone_playback_state_changed)
        self._clone_playback.error_occurred.connect(self._show_clone_playback_error)

    def _request_synthesis(self) -> None:
        self._playback.clear()
        self.waveform.clear()
        voice_id = self.voice_selector.current_voice_id()
        voice_artifact_path = self.voice_selector.current_voice_artifact_path()
        if voice_artifact_path is None and voice_id is not None:
            voice_artifact_path = self._cloned_voice_artifacts.get(voice_id)
        self._view_model.synthesize(
            self.text_input.text(),
            self.voice_style.effects(),
            voice_id,
            self.voice_style.current_style_id(),
            voice_artifact_path=voice_artifact_path,
        )

    def _enroll_voice(self, name: str, source_audio_path: str) -> None:
        self._clone_enrollment_pending = True
        self._view_model.enroll_voice(name, source_audio_path)

    def _voice_profile_created(self, profile: object) -> None:
        self._clone_enrollment_pending = False
        self.voice_clone_page.profile_created(profile)

    def _preview_cloned_voice(self, profile: object) -> None:
        artifact_path = str(getattr(profile, "voice_artifact_path", ""))
        profile_id = str(getattr(profile, "profile_id", ""))
        if not artifact_path or not profile_id:
            self.voice_clone_page.enrollment_failed(
                "Hồ sơ không có dữ liệu đặc điểm giọng hợp lệ."
            )
            return
        self._clone_playback.clear()
        self._clone_preview_pending = True
        self._clone_preview_active = False
        self.voice_clone_page.set_preview_state("synthesizing")
        self._view_model.synthesize(
            "Xin chào, đây là bản nghe thử giọng nói đã nhân bản.",
            AudioEffects(),
            f"clone:{profile_id}",
            "tu_nhien",
            voice_artifact_path=artifact_path,
            engine_id_override=VIENEU_V3_ENGINE_ID,
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
        self._engine_voices = list(voices)
        self._refresh_voice_choices()
        self._refresh_actions()

    def _capabilities_changed(self, capabilities: object) -> None:
        style_ids = tuple(getattr(capabilities, "supported_style_ids", ("tu_nhien",)))
        self.voice_style.set_supported_styles(style_ids)
        self._refresh_voice_choices()

    def _show_page(self, index: int) -> None:
        if index == 0:
            if self._clone_preview_pending:
                self._clone_preview_pending = False
                self._view_model.cancel_current_task()
                self.voice_clone_page.set_preview_state("stopped")
            self._clone_playback.stop()
        else:
            self._playback.stop()
        self.page_stack.setCurrentIndex(index)
        self.nav_compose_button.setChecked(index == 0)
        self.nav_clone_button.setChecked(index == 1)
        self.nav_settings_button.setChecked(index == 2)
        self.nav_contact_button.setChecked(index == 3)

    def _runtime_changed(self, runtime: object) -> None:
        self.active_model_card.set_runtime(runtime)
        self.model_settings_page.set_runtime(runtime)

    def _hardware_changed(self, hardware: object) -> None:
        self.model_settings_page.set_hardware(
            hardware,
            self._settings.hardware_recommendation.high_tier.min_vram_gb,
        )
        self.active_model_card.set_hardware(hardware)

    def _profiles_changed(self, profiles: list) -> None:
        self._cloned_voice_artifacts = {
            f"clone:{profile.profile_id}": profile.voice_artifact_path
            for profile in profiles
            if profile.status == "ready"
        }
        self._refresh_voice_choices()

    def _refresh_voice_choices(self) -> None:
        voices = list(self._engine_voices)
        capabilities = self._view_model.selected_capabilities
        if (
            self._view_model.selected_engine_id == VIENEU_V3_ENGINE_ID
            and bool(getattr(capabilities, "voice_cloning", False))
        ):
            profiles_by_id = {
                profile.profile_id: profile for profile in self.voice_clone_page.profiles
            }
            voices.extend(
                VoiceInfo(voice_id, profiles_by_id[voice_id.removeprefix("clone:")].name, True)
                for voice_id in self._cloned_voice_artifacts
                if voice_id.removeprefix("clone:") in profiles_by_id
            )
        self.voice_selector.set_voices(voices, self._cloned_voice_artifacts)

    def _state_changed(self, state: str) -> None:
        messages = {
            "idle": "Sẵn sàng tạo giọng nói.",
            "loading_engine": "Đang kiểm tra và tải model vào GPU...",
            "importing_document": "Đang đọc và trích xuất văn bản từ tệp...",
            "synthesizing": "Đang tạo giọng nói...",
            "enrolling_voice": "Đang rút và lưu đặc điểm giọng...",
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
            "enrolling_voice": "busy",
            "completed": "success",
            "error": "error",
            "cancelled": "warning",
        }
        self._set_status_style(status_style[state])
        busy = state in {
            "loading_engine",
            "importing_document",
            "synthesizing",
            "enrolling_voice",
        }
        self.cancel_button.setEnabled(busy)
        self.cancel_button.setVisible(busy)
        self.model_settings_page.set_loading(state == "loading_engine")
        self.text_input.open_file_button.setEnabled(not busy)
        self.text_input.editor.setReadOnly(state == "importing_document")
        self._refresh_actions()

    def _show_error(self, message: str) -> None:
        if self._clone_enrollment_pending:
            self._clone_enrollment_pending = False
            self.voice_clone_page.enrollment_failed(message)
        if self._clone_preview_pending or self._clone_preview_active:
            self._clone_preview_pending = False
            self._clone_preview_active = False
            self.voice_clone_page.preview_failed(message)
        self.status_label.setText(f"●  Lỗi: {message}")
        self._set_status_style("error")
        self._refresh_actions()

    def _synthesis_completed(self, result: SynthesisResult) -> None:
        if self._clone_preview_pending:
            self._clone_preview_pending = False
            self._clone_preview_active = True
            try:
                self._clone_playback.set_audio(result)
                self._clone_playback.play()
            except PlaybackError as exc:
                self._show_clone_playback_error(str(exc))
            return

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

    def _export_audio(self, audio_format: str) -> None:
        upper_format = audio_format.upper()
        destination, _selected_filter = QFileDialog.getSaveFileName(
            self,
            f"Xuất file {upper_format}",
            f"giong-noi.{audio_format}",
            f"Audio {upper_format} (*.{audio_format})",
        )
        if not destination:
            return
        try:
            output_path = self._playback.export_audio(destination, audio_format)
        except PlaybackError as exc:
            self._show_playback_error(str(exc))
            return
        self.status_label.setText(f"●  Đã xuất {output_path.name}")
        self._set_status_style("success")

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

    def _clone_playback_state_changed(self, state: str) -> None:
        if not self._clone_preview_active:
            return
        self.voice_clone_page.set_preview_state(state)
        if state in {"stopped", "empty"}:
            self._clone_preview_active = False

    def _show_clone_playback_error(self, message: str) -> None:
        self._clone_preview_pending = False
        self._clone_preview_active = False
        self.voice_clone_page.preview_failed(message)

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
            not in {
                "loading_engine",
                "importing_document",
                "synthesizing",
                "enrolling_voice",
            }
        )
        self.synthesize_button.setEnabled(ready)
        has_audio = self._playback.has_audio
        self.export_wav_button.setEnabled(has_audio)
        self.export_mp3_button.setEnabled(has_audio)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Reflow cards when the window crosses a responsive breakpoint."""

        super().resizeEvent(event)
        if hasattr(self, "_workspace_layout"):
            content_width = max(0, event.size().width() - THEME.sidebar_width)
            self._apply_responsive_layout(content_width)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Release worker and engine resources before closing."""

        self._clone_playback.shutdown()
        self._playback.shutdown()
        self._view_model.shutdown()
        super().closeEvent(event)
