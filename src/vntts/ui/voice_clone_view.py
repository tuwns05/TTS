"""Voice-profile creation and management page for VieNeu v3."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QAction, QResizeEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QBoxLayout,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from vntts.config.theme import THEME
from vntts.services.voice_profiles import VoiceProfile, VoiceProfileStore
from vntts.utils.exceptions import AppError


class VoiceClonePage(QWidget):
    """Upload reference audio and manage reusable numerical voice profiles."""

    profiles_changed = Signal(object)
    enrollment_requested = Signal(str, str)
    preview_requested = Signal(object)
    stop_preview_requested = Signal()

    def __init__(self, store: VoiceProfileStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("voiceClonePage")
        self.setMinimumWidth(0)
        self._store = store
        self._selected_audio: Path | None = None
        self._enrolling = False
        self._preview_state = "stopped"
        self._active_preview_profile_id: str | None = None
        self._preview_buttons: dict[str, QPushButton] = {}
        self._preview_fallback_button = QPushButton("Nghe thử", self)
        self._preview_fallback_button.setEnabled(False)
        self._preview_fallback_button.hide()
        self._profile_row_layouts: list[QBoxLayout] = []
        self._responsive_mode = ""

        title = QLabel("Nhân bản giọng nói", self)
        title.setProperty("role", "title")
        self.voice_clone_help_button = QPushButton("Hướng dẫn", self)
        self.voice_clone_help_button.setObjectName("voiceCloneHelpButton")
        self.voice_clone_help_button.setProperty("variant", "help")
        self.voice_clone_help_button.setAccessibleName(
            "Mở hướng dẫn nhân bản giọng nói"
        )
        self.voice_clone_help_button.setToolTip(
            "Xem hướng dẫn chuẩn bị mẫu và tạo hồ sơ giọng"
        )
        self.voice_clone_help_button.setFixedHeight(30)
        page_header = QHBoxLayout()
        page_header.setContentsMargins(0, 0, 0, 0)
        page_header.setSpacing(THEME.space_2)
        page_header.addWidget(title)
        page_header.addStretch()
        page_header.addWidget(self.voice_clone_help_button)
        description = QLabel(
            "Tạo hồ sơ giọng từ một đoạn ghi âm ngắn. Mẫu âm thanh chỉ dùng để "
            "trích xuất đặc trưng giọng và không được lưu lại.",
            self,
        )
        description.setProperty("role", "secondary")
        description.setWordWrap(True)
        description.setMaximumWidth(THEME.content_reading_width)
        description.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )

        form = QFrame(self)
        form.setObjectName("voiceProfileFormCard")
        form.setProperty("card", True)
        form_title = QLabel("Tạo hồ sơ giọng mới", form)
        form_title.setProperty("role", "section")
        name_label = QLabel("Tên hồ sơ", form)
        name_label.setObjectName("fieldLabel")
        self.name_input = QLineEdit(form)
        self.name_input.setObjectName("voiceProfileName")
        self.name_input.setPlaceholderText("Ví dụ: Giọng của tôi")
        self.name_input.setAccessibleName("Tên hồ sơ giọng")
        sample_label = QLabel("Mẫu giọng", form)
        sample_label.setObjectName("fieldLabel")

        self.audio_file_card = QFrame(form)
        self.audio_file_card.setObjectName("voiceSampleFileSelector")
        self.audio_file_card.setProperty("fileSelector", True)
        self.audio_file_card.setProperty("hasFile", False)
        self.audio_file_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        selector_icon = QLabel(self.audio_file_card)
        selector_icon.setObjectName("voiceSampleIcon")
        selector_icon.setPixmap(
            self.style()
            .standardIcon(QStyle.StandardPixmap.SP_FileIcon)
            .pixmap(QSize(THEME.icon_size, THEME.icon_size))
        )
        selector_icon.setFixedSize(THEME.space_6, THEME.space_6)
        selector_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.audio_label = QLabel("Chưa chọn mẫu giọng", self.audio_file_card)
        self.audio_label.setObjectName("voiceSampleFileName")
        self.audio_label.setWordWrap(True)
        self.audio_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.audio_meta_label = QLabel(
            "WAV, MP3, FLAC · Khuyến nghị 6–8 giây", self.audio_file_card
        )
        self.audio_meta_label.setProperty("role", "caption")
        self.audio_meta_label.setWordWrap(True)
        self.audio_meta_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        selector_text = QWidget(self.audio_file_card)
        selector_text_layout = QVBoxLayout(selector_text)
        selector_text_layout.setContentsMargins(0, 0, 0, 0)
        selector_text_layout.setSpacing(THEME.space_1)
        selector_text_layout.addWidget(self.audio_label)
        selector_text_layout.addWidget(self.audio_meta_label)
        selector_info = QWidget(self.audio_file_card)
        selector_info_layout = QHBoxLayout(selector_info)
        selector_info_layout.setContentsMargins(0, 0, 0, 0)
        selector_info_layout.setSpacing(THEME.space_3)
        selector_info_layout.addWidget(selector_icon)
        selector_info_layout.addWidget(selector_text, 1)
        self.upload_button = QPushButton("Chọn file", self.audio_file_card)
        self.upload_button.setObjectName("uploadVoiceButton")
        self.upload_button.setProperty("variant", "secondary")
        self.clear_audio_button = QPushButton("Xóa", self.audio_file_card)
        self.clear_audio_button.setObjectName("clearVoiceSampleButton")
        self.clear_audio_button.setProperty("variant", "ghost")
        self.clear_audio_button.setAccessibleName("Bỏ file mẫu giọng đã chọn")
        self.clear_audio_button.setToolTip("Bỏ file mẫu đã chọn")
        self.clear_audio_button.hide()
        selector_actions = QWidget(self.audio_file_card)
        selector_actions_layout = QHBoxLayout(selector_actions)
        selector_actions_layout.setContentsMargins(0, 0, 0, 0)
        selector_actions_layout.setSpacing(THEME.space_2)
        selector_actions_layout.addWidget(self.clear_audio_button)
        selector_actions_layout.addWidget(self.upload_button)
        self._file_selector_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._file_selector_layout.setContentsMargins(
            THEME.space_4, THEME.space_3, THEME.space_3, THEME.space_3
        )
        self._file_selector_layout.setSpacing(THEME.space_3)
        self._file_selector_layout.addWidget(selector_info, 1)
        self._file_selector_layout.addWidget(selector_actions, 0)
        self.audio_file_card.setLayout(self._file_selector_layout)
        self.empty_audio_label = self.audio_meta_label

        self.sample_note = QLabel(
            "Gợi ý: Chọn file có 6–8 giây giọng nói rõ, chỉ một người nói, "
            "phòng yên tĩnh; tránh nhạc nền, tiếng vọng và âm lượng quá lớn gây vỡ tiếng.",
            form,
        )
        self.sample_note.setObjectName("voiceSampleNote")
        self.sample_note.setProperty("role", "caption")
        self.sample_note.setWordWrap(True)
        self.sample_note.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.create_button = QPushButton("Tạo hồ sơ giọng", form)
        self.create_button.setObjectName("createVoiceProfileButton")
        self.create_button.setProperty("variant", "primary")
        self.create_button.setEnabled(False)
        self.processing_label = QLabel("●  Chờ mẫu giọng", form)
        self.processing_label.setObjectName("profileStatusLabel")
        self.processing_label.setProperty("state", "neutral")
        self.processing_label.setWordWrap(True)
        self._form_footer = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._form_footer.setContentsMargins(0, THEME.space_1, 0, 0)
        self._form_footer.setSpacing(THEME.space_3)
        self._form_footer.addWidget(self.processing_label, 1)
        self._form_footer.addWidget(self.create_button, 0)

        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(
            THEME.space_5, THEME.space_5, THEME.space_5, THEME.space_5
        )
        form_layout.setSpacing(THEME.space_3)
        form_layout.addWidget(form_title)
        form_layout.addSpacing(THEME.space_1)
        form_layout.addWidget(name_label)
        form_layout.addWidget(self.name_input)
        form_layout.addWidget(sample_label)
        form_layout.addWidget(self.audio_file_card)
        form_layout.addWidget(self.sample_note)
        form_layout.addLayout(self._form_footer)

        profiles_section = QWidget(self)
        profiles_section.setObjectName("voiceProfilesSection")
        profiles_title = QLabel("Hồ sơ giọng", profiles_section)
        profiles_title.setProperty("role", "section")
        self.profile_count_label = QLabel("0 hồ sơ", profiles_section)
        self.profile_count_label.setProperty("role", "secondary")
        profiles_header = QHBoxLayout()
        profiles_header.setContentsMargins(0, 0, 0, 0)
        profiles_header.addWidget(profiles_title)
        profiles_header.addStretch()
        profiles_header.addWidget(self.profile_count_label)

        self.empty_profiles = QFrame(profiles_section)
        self.empty_profiles.setObjectName("voiceProfilesEmptyState")
        self.empty_profiles.setProperty("emptyState", True)
        empty_title = QLabel("Chưa có hồ sơ giọng", self.empty_profiles)
        empty_title.setProperty("role", "section")
        empty_description = QLabel(
            "Tạo hồ sơ giọng đầu tiên từ mẫu ghi âm phía trên.",
            self.empty_profiles,
        )
        empty_description.setProperty("role", "secondary")
        empty_description.setWordWrap(True)
        empty_description.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        empty_layout = QVBoxLayout(self.empty_profiles)
        empty_layout.setContentsMargins(
            THEME.space_4, THEME.space_4, THEME.space_4, THEME.space_4
        )
        empty_layout.setSpacing(THEME.space_1)
        empty_layout.addWidget(empty_title)
        empty_layout.addWidget(empty_description)

        self.profile_list = QListWidget(profiles_section)
        self.profile_list.setObjectName("voiceProfileList")
        self.profile_list.setAccessibleName("Danh sách hồ sơ giọng")
        self.profile_list.setSpacing(THEME.space_2)
        self.profile_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.profile_list.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self.profile_list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        profiles_layout = QVBoxLayout(profiles_section)
        profiles_layout.setContentsMargins(0, 0, 0, 0)
        profiles_layout.setSpacing(THEME.space_3)
        profiles_layout.addLayout(profiles_header)
        profiles_layout.addWidget(self.empty_profiles)
        profiles_layout.addWidget(self.profile_list)

        self._page_layout = QVBoxLayout(self)
        self._page_layout.setContentsMargins(
            THEME.space_5, THEME.space_5, THEME.space_5, THEME.space_5
        )
        self._page_layout.setSpacing(THEME.space_4)
        self._page_layout.addLayout(page_header)
        self._page_layout.addWidget(description)
        self._page_layout.addWidget(form)
        self._page_layout.addSpacing(THEME.space_2)
        self._page_layout.addWidget(profiles_section)
        self._page_layout.addStretch()

        self.upload_button.clicked.connect(self._choose_audio)
        self.clear_audio_button.clicked.connect(self._clear_selected_audio)
        self.create_button.clicked.connect(self._create_profile)
        self.voice_clone_help_button.clicked.connect(self._show_voice_clone_help)
        self.profile_list.currentItemChanged.connect(self._selection_changed)
        self.name_input.textChanged.connect(self._refresh_create_button)
        self._reload_profiles()

    def _show_voice_clone_help(self) -> None:
        """Explain how to prepare audio and create a reusable voice profile."""

        QMessageBox.information(
            self,
            "Hướng dẫn nhân bản giọng nói",
            "1. Nhập tên dễ nhận biết cho hồ sơ giọng.\n"
            "2. Chọn file WAV, MP3 hoặc FLAC có một người nói rõ ràng.\n"
            "3. Nên dùng đoạn ghi âm dài 6–8 giây, không có nhạc nền, tiếng vọng "
            "hoặc tạp âm lớn.\n"
            "4. Bấm 'Tạo hồ sơ giọng' và chờ xử lý hoàn tất.\n"
            "5. Dùng nút 'Nghe thử' để kiểm tra hoặc chọn hồ sơ tại trang "
            "Tạo giọng nói.\n\n"
            "Ứng dụng chỉ lưu đặc trưng giọng đã trích xuất; file âm thanh gốc "
            "không được sao chép vào hồ sơ.",
            QMessageBox.StandardButton.Ok,
        )

    @property
    def profiles(self) -> list[VoiceProfile]:
        return self._store.list_profiles()

    def _choose_audio(self) -> None:
        source, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Chọn mẫu giọng",
            "",
            "Audio (*.wav *.mp3 *.flac *.m4a *.ogg)",
        )
        if source:
            self._set_selected_audio(Path(source))

    def _set_selected_audio(self, source: Path) -> None:
        self._selected_audio = source
        self.audio_label.setText(source.name)
        self.audio_label.setToolTip(str(source))
        self.audio_meta_label.setText("Mẫu giọng đã sẵn sàng")
        self.upload_button.setText("Thay đổi")
        self.clear_audio_button.show()
        self.audio_file_card.setProperty("hasFile", True)
        self._refresh_style(self.audio_file_card)
        self.processing_label.setText("●  Mẫu giọng đã sẵn sàng")
        self._set_status("success")
        self._refresh_create_button()

    def _clear_selected_audio(self) -> None:
        """Forget the selected sample without deleting the user's source file."""

        if self._enrolling:
            return
        self._selected_audio = None
        self.audio_label.setText("Chưa chọn mẫu giọng")
        self.audio_label.setToolTip("")
        self.audio_meta_label.setText("WAV, MP3, FLAC · Khuyến nghị 6–8 giây")
        self.upload_button.setText("Chọn file")
        self.clear_audio_button.hide()
        self.audio_file_card.setProperty("hasFile", False)
        self._refresh_style(self.audio_file_card)
        self.processing_label.setText("●  Chờ mẫu giọng")
        self._set_status("neutral")
        self._refresh_create_button()

    def _create_profile(self) -> None:
        if self._selected_audio is None:
            return
        self._enrolling = True
        self.processing_label.setText("●  Đang tạo hồ sơ...")
        self._set_status("busy")
        self._refresh_create_button()
        self.enrollment_requested.emit(
            self.name_input.text(),
            str(self._selected_audio),
        )

    def profile_created(self, profile: VoiceProfile) -> None:
        """Finish the enrollment UI after the worker persisted its features."""

        self._enrolling = False
        self.name_input.clear()
        self._selected_audio = None
        self.audio_label.setText("Chưa chọn mẫu giọng")
        self.audio_label.setToolTip("")
        self.audio_meta_label.setText("WAV, MP3, FLAC · Khuyến nghị 6–8 giây")
        self.upload_button.setText("Chọn file")
        self.clear_audio_button.hide()
        self.audio_file_card.setProperty("hasFile", False)
        self._refresh_style(self.audio_file_card)
        if profile.warnings:
            self.processing_label.setText(
                "●  Hồ sơ đã lưu · Cảnh báo: " + " ".join(profile.warnings)
            )
            self._set_status("warning")
        else:
            self.processing_label.setText("●  Tạo hồ sơ thành công")
            self._set_status("success")
        self._reload_profiles(profile.profile_id)
        self._refresh_create_button()

    def enrollment_failed(self, message: str) -> None:
        """Restore controls and present a concise enrollment error."""

        self._enrolling = False
        self.processing_label.setText(f"●  Lỗi: {message}")
        self._set_status("error")
        self._refresh_create_button()

    def preview_failed(self, message: str) -> None:
        """Present an error from the cloned-voice preview player."""

        self.set_preview_state("stopped")
        self.processing_label.setText(f"●  Lỗi nghe thử: {message}")
        self._set_status("error")

    def _rename_profile(self, profile: VoiceProfile | None = None) -> None:
        profile = profile or self._current_profile()
        if profile is None:
            return
        name, accepted = QInputDialog.getText(
            self, "Sửa hồ sơ giọng", "Tên mới", text=profile.name
        )
        if accepted:
            try:
                self._store.rename(profile.profile_id, name)
            except AppError as exc:
                self.processing_label.setText(f"●  Lỗi: {exc}")
                self._set_status("error")
                return
            self._reload_profiles(profile.profile_id)

    def _delete_profile(self, profile: VoiceProfile | None = None) -> None:
        profile = profile or self._current_profile()
        if profile is None:
            return
        answer = QMessageBox.question(
            self,
            "Xóa hồ sơ giọng",
            f"Xóa hồ sơ '{profile.name}' và đặc điểm giọng đã lưu?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.stop_preview_requested.emit()
        if self._active_preview_profile_id == profile.profile_id:
            self._active_preview_profile_id = None
            self._preview_state = "stopped"
        try:
            self._store.delete(profile.profile_id)
        except AppError as exc:
            self.processing_label.setText(f"●  Lỗi: {exc}")
            self._set_status("error")
            return
        self.processing_label.setText("●  Đã xóa hồ sơ giọng")
        self._set_status("neutral")
        self._reload_profiles()

    def _reload_profiles(self, selected_profile_id: str | None = None) -> None:
        profiles = self._store.list_profiles()
        self._preview_buttons.clear()
        self._profile_row_layouts.clear()
        self.profile_list.clear()
        self.profile_count_label.setText(f"{len(profiles)} hồ sơ")
        self.empty_profiles.setVisible(not profiles)
        self.profile_list.setVisible(bool(profiles))
        for profile in profiles:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, profile)
            item.setData(Qt.ItemDataRole.AccessibleTextRole, profile.name)
            self.profile_list.addItem(item)
            row = QFrame(self.profile_list)
            row.setObjectName("voiceProfileRow")
            row.setProperty("profileCard", True)
            row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

            voice_icon = QLabel(row)
            voice_icon.setObjectName("voiceProfileIcon")
            voice_icon.setPixmap(
                self.style()
                .standardIcon(QStyle.StandardPixmap.SP_MediaVolume)
                .pixmap(QSize(THEME.icon_size, THEME.icon_size))
            )
            voice_icon.setFixedSize(THEME.space_6, THEME.space_6)
            voice_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_label = QLabel(profile.name, row)
            name_label.setObjectName("voiceProfileRowName")
            name_label.setToolTip(profile.name)
            state_label = QLabel("●  Sẵn sàng", row)
            state_label.setObjectName("voiceProfileState")
            state_label.setProperty("profileState", True)
            state_label.setProperty("state", "success")
            profile_text = QWidget(row)
            profile_text_layout = QVBoxLayout(profile_text)
            profile_text_layout.setContentsMargins(0, 0, 0, 0)
            profile_text_layout.setSpacing(THEME.space_1)
            profile_text_layout.addWidget(name_label)
            profile_text_layout.addWidget(state_label)
            profile_identity = QWidget(row)
            profile_identity_layout = QHBoxLayout(profile_identity)
            profile_identity_layout.setContentsMargins(0, 0, 0, 0)
            profile_identity_layout.setSpacing(THEME.space_3)
            profile_identity_layout.addWidget(voice_icon)
            profile_identity_layout.addWidget(profile_text, 1)

            preview_button = QPushButton("Nghe thử", row)
            preview_button.setObjectName("previewVoiceProfileButton")
            preview_button.setProperty("variant", "secondary")
            preview_button.setAccessibleName(f"Nghe thử giọng {profile.name}")
            preview_button.setIcon(
                self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
            )
            preview_button.setIconSize(QSize(THEME.icon_size, THEME.icon_size))
            preview_button.clicked.connect(
                lambda _checked=False, selected=profile: self._toggle_preview(selected)
            )
            self._preview_buttons[profile.profile_id] = preview_button

            more_button = QToolButton(row)
            more_button.setObjectName("voiceProfileMenuButton")
            more_button.setText("⋮")
            more_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            more_button.setAccessibleName(f"Thao tác với hồ sơ {profile.name}")
            more_button.setToolTip("Thao tác khác")
            menu = QMenu(more_button)
            menu.setObjectName("voiceProfileMenu")
            rename_action = QAction("Đổi tên", menu)
            delete_action = QAction("Xóa hồ sơ", menu)
            delete_action.setProperty("destructive", True)
            delete_action.setIcon(
                self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon)
            )
            rename_action.triggered.connect(
                lambda _checked=False, selected=profile: self._rename_profile(selected)
            )
            delete_action.triggered.connect(
                lambda _checked=False, selected=profile: self._delete_profile(selected)
            )
            menu.addAction(rename_action)
            menu.addSeparator()
            menu.addAction(delete_action)
            more_button.setMenu(menu)
            more_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            profile_actions = QWidget(row)
            profile_actions_layout = QHBoxLayout(profile_actions)
            profile_actions_layout.setContentsMargins(0, 0, 0, 0)
            profile_actions_layout.setSpacing(THEME.space_2)
            profile_actions_layout.addStretch()
            profile_actions_layout.addWidget(preview_button)
            profile_actions_layout.addWidget(more_button)

            row_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, row)
            row_layout.setContentsMargins(
                THEME.space_4, THEME.space_3, THEME.space_3, THEME.space_3
            )
            row_layout.setSpacing(THEME.space_3)
            row_layout.addWidget(profile_identity, 1)
            row_layout.addWidget(profile_actions, 0)
            self._profile_row_layouts.append(row_layout)
            item.setSizeHint(QSize(0, THEME.clone_profile_row_height))
            self.profile_list.setItemWidget(item, row)
            if profile.profile_id == selected_profile_id:
                self.profile_list.setCurrentItem(item)
        if selected_profile_id is not None:
            self._active_preview_profile_id = selected_profile_id
        self._update_profile_list_height()
        self._sync_preview_buttons()
        self._apply_responsive_layout(self.width())
        self.profiles_changed.emit(profiles)

    def _current_profile(self) -> VoiceProfile | None:
        item = self.profile_list.currentItem()
        value = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        return value if isinstance(value, VoiceProfile) else None

    def _selection_changed(self, current: QListWidgetItem | None, _previous: object) -> None:
        if current is not None:
            current.setSelected(False)
        for index in range(self.profile_list.count()):
            item = self.profile_list.item(index)
            row = self.profile_list.itemWidget(item)
            if row is not None:
                row.setProperty("selected", item is current)
                row.style().unpolish(row)
                row.style().polish(row)

    @property
    def preview_button(self) -> QPushButton:
        """Return the selected row's preview control for compatibility/tests."""

        profile = self._current_profile()
        if profile is not None and profile.profile_id in self._preview_buttons:
            return self._preview_buttons[profile.profile_id]
        if self._preview_buttons:
            return next(iter(self._preview_buttons.values()))
        return self._preview_fallback_button

    def _toggle_preview(self, profile: VoiceProfile) -> None:
        if (
            self._active_preview_profile_id == profile.profile_id
            and self._preview_state == "playing"
        ):
            self.stop_preview_requested.emit()
            return
        self._active_preview_profile_id = profile.profile_id
        self._preview_state = "synthesizing"
        self._select_profile(profile.profile_id)
        self._sync_preview_buttons()
        self.processing_label.setText("●  Đang tạo bản nghe thử...")
        self._set_status("busy")
        self.preview_requested.emit(profile)

    def _select_profile(self, profile_id: str) -> None:
        for index in range(self.profile_list.count()):
            item = self.profile_list.item(index)
            profile = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(profile, VoiceProfile) and profile.profile_id == profile_id:
                self.profile_list.setCurrentItem(item)
                return

    def set_preview_state(self, state: str) -> None:
        """Reflect synthesis/playback state for the cloned-voice preview."""

        self._preview_state = state
        self._sync_preview_buttons()
        if state == "playing":
            self.processing_label.setText("●  Đang phát bản nghe thử")
            self._set_status("busy")
        elif state == "stopped":
            self.processing_label.setText("●  Đã dừng nghe thử")
            self._set_status("neutral")
        elif state == "ready":
            self.processing_label.setText("●  Giọng clone sẵn sàng")
            self._set_status("success")

    def _sync_preview_buttons(self) -> None:
        for profile_id, button in self._preview_buttons.items():
            is_active = profile_id == self._active_preview_profile_id
            if is_active and self._preview_state == "playing":
                button.setText("Dừng")
                button.setIcon(
                    self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop)
                )
                button.setEnabled(True)
            elif is_active and self._preview_state == "synthesizing":
                button.setText("Đang tạo...")
                button.setIcon(
                    self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
                )
                button.setEnabled(False)
            else:
                button.setText("Nghe thử")
                button.setIcon(
                    self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
                )
                button.setEnabled(self._preview_state != "synthesizing")

    def _update_profile_list_height(self) -> None:
        count = self.profile_list.count()
        if count == 0:
            return
        row_height = (
            THEME.clone_profile_row_height + THEME.space_6
            if self._responsive_mode == "narrow"
            else THEME.clone_profile_row_height
        )
        for index in range(count):
            self.profile_list.item(index).setSizeHint(QSize(0, row_height))
        visible_rows = min(count, THEME.clone_profile_list_max_rows)
        spacing = self.profile_list.spacing()
        self.profile_list.setFixedHeight(
            visible_rows * row_height + (visible_rows + 1) * spacing
        )

    def _apply_responsive_layout(self, width: int) -> None:
        mode = "narrow" if width < THEME.narrow_content_breakpoint else "wide"
        if mode == self._responsive_mode:
            return
        self._responsive_mode = mode
        if mode == "narrow":
            self._page_layout.setContentsMargins(
                THEME.space_3, THEME.space_3, THEME.space_3, THEME.space_4
            )
            self._file_selector_layout.setDirection(QBoxLayout.Direction.TopToBottom)
            self._form_footer.setDirection(QBoxLayout.Direction.TopToBottom)
            self._form_footer.setAlignment(
                self.create_button, Qt.AlignmentFlag.AlignRight
            )
            for row_layout in self._profile_row_layouts:
                row_layout.setDirection(QBoxLayout.Direction.TopToBottom)
        else:
            self._page_layout.setContentsMargins(
                THEME.space_5, THEME.space_5, THEME.space_5, THEME.space_5
            )
            self._file_selector_layout.setDirection(QBoxLayout.Direction.LeftToRight)
            self._form_footer.setDirection(QBoxLayout.Direction.LeftToRight)
            self._form_footer.setAlignment(
                self.create_button, Qt.AlignmentFlag.AlignVCenter
            )
            for row_layout in self._profile_row_layouts:
                row_layout.setDirection(QBoxLayout.Direction.LeftToRight)
        self._update_profile_list_height()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._apply_responsive_layout(event.size().width())

    def _refresh_create_button(self) -> None:
        self.name_input.setEnabled(not self._enrolling)
        self.upload_button.setEnabled(not self._enrolling)
        self.clear_audio_button.setEnabled(
            not self._enrolling and self._selected_audio is not None
        )
        self.create_button.setEnabled(
            not self._enrolling
            and bool(self.name_input.text().strip())
            and self._selected_audio is not None
        )

    def _set_status(self, state: str) -> None:
        self.processing_label.setProperty("state", state)
        self._refresh_style(self.processing_label)

    @staticmethod
    def _refresh_style(widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()
