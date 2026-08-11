"""Voice-profile creation and management page for VieNeu v3."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

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
        self._store = store
        self._selected_audio: Path | None = None
        self._enrolling = False

        title = QLabel("Nhân bản giọng", self)
        title.setObjectName("appTitle")
        description = QLabel(
            "Tạo hồ sơ từ một mẫu giọng rõ ràng. VieNeu v3 rút đặc điểm giọng một lần; app không lưu file âm thanh mẫu.",
            self,
        )
        description.setObjectName("appSubtitle")
        description.setWordWrap(True)

        form = QFrame(self)
        form.setObjectName("composerCard")
        self.name_input = QLineEdit(form)
        self.name_input.setObjectName("voiceProfileName")
        self.name_input.setPlaceholderText("Ví dụ: Giọng của tôi")
        self.name_input.setAccessibleName("Tên hồ sơ giọng")
        self.audio_label = QLabel("Chưa chọn mẫu giọng", form)
        self.audio_label.setObjectName("helperText")
        self.upload_button = QPushButton("Tải file mẫu", form)
        self.upload_button.setObjectName("uploadVoiceButton")
        self.sample_note = QLabel(
            "Gợi ý: Chọn file có 6–8 giây giọng nói rõ, chỉ một người nói, "
            "phòng yên tĩnh; tránh nhạc nền, tiếng vọng và âm lượng quá lớn gây vỡ tiếng.",
            form,
        )
        self.sample_note.setObjectName("voiceSampleNote")
        self.sample_note.setProperty("role", "caption")
        self.sample_note.setWordWrap(True)
        self.create_button = QPushButton("Tạo hồ sơ giọng", form)
        self.create_button.setObjectName("createVoiceProfileButton")
        self.create_button.setEnabled(False)
        self.processing_label = QLabel("●  Chờ mẫu giọng", form)
        self.processing_label.setObjectName("profileStatusLabel")
        self.processing_label.setProperty("state", "neutral")
        self.processing_label.setWordWrap(True)

        source_actions = QHBoxLayout()
        source_actions.addWidget(self.upload_button)
        source_actions.addStretch()
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(22, 22, 22, 22)
        form_layout.setSpacing(12)
        form_layout.addWidget(QLabel("Tên hồ sơ", form))
        form_layout.addWidget(self.name_input)
        form_layout.addWidget(QLabel("Mẫu giọng", form))
        form_layout.addLayout(source_actions)
        form_layout.addWidget(self.audio_label)
        form_layout.addWidget(self.sample_note)
        form_layout.addWidget(self.processing_label)
        form_layout.addWidget(self.create_button)

        profiles_card = QFrame(self)
        profiles_card.setObjectName("playerCard")
        profiles_title = QLabel("Hồ sơ giọng đã tạo", profiles_card)
        profiles_title.setObjectName("playerTitle")
        self.profile_list = QListWidget(profiles_card)
        self.profile_list.setObjectName("voiceProfileList")
        self.profile_list.setAccessibleName("Danh sách hồ sơ giọng")
        self.rename_button = QPushButton("Sửa tên", profiles_card)
        self.delete_button = QPushButton("Xóa", profiles_card)
        self.preview_button = QPushButton("Nghe thử giọng clone", profiles_card)
        self.preview_button.setAccessibleName("Tổng hợp câu nghe thử bằng giọng clone")
        self.stop_preview_button = QPushButton("Dừng nghe", profiles_card)
        self.rename_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.preview_button.setEnabled(False)
        self.stop_preview_button.setEnabled(False)
        profile_actions = QHBoxLayout()
        profile_actions.addWidget(self.preview_button)
        profile_actions.addWidget(self.stop_preview_button)
        profile_actions.addStretch()
        profile_actions.addWidget(self.rename_button)
        profile_actions.addWidget(self.delete_button)
        profiles_layout = QVBoxLayout(profiles_card)
        profiles_layout.setContentsMargins(22, 22, 22, 22)
        profiles_layout.setSpacing(12)
        profiles_layout.addWidget(profiles_title)
        profiles_layout.addWidget(self.profile_list, 1)
        profiles_layout.addLayout(profile_actions)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(18)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(form)
        layout.addWidget(profiles_card, 1)

        self.upload_button.clicked.connect(self._choose_audio)
        self.create_button.clicked.connect(self._create_profile)
        self.profile_list.currentItemChanged.connect(self._selection_changed)
        self.rename_button.clicked.connect(self._rename_profile)
        self.delete_button.clicked.connect(self._delete_profile)
        self.preview_button.clicked.connect(self._play_selected_profile)
        self.stop_preview_button.clicked.connect(self.stop_preview_requested)
        self.name_input.textChanged.connect(self._refresh_create_button)
        self._reload_profiles()

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
        self.processing_label.setText("●  Mẫu giọng đã sẵn sàng để xử lý")
        self._set_status("success")
        self._refresh_create_button()

    def _create_profile(self) -> None:
        if self._selected_audio is None:
            return
        self._enrolling = True
        self.processing_label.setText("●  Đang để VieNeu rút đặc điểm giọng...")
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
        if profile.warnings:
            self.processing_label.setText(
                "●  Hồ sơ đã lưu · Cảnh báo: " + " ".join(profile.warnings)
            )
            self._set_status("busy")
        else:
            self.processing_label.setText("●  Đã lưu đặc điểm giọng · Sẵn sàng")
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

    def _rename_profile(self) -> None:
        profile = self._current_profile()
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
            self._reload_profiles()

    def _delete_profile(self) -> None:
        profile = self._current_profile()
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
        self.profile_list.clear()
        for profile in profiles:
            item = QListWidgetItem(f"{profile.name}  ·  Sẵn sàng")
            item.setData(Qt.ItemDataRole.UserRole, profile)
            self.profile_list.addItem(item)
            if profile.profile_id == selected_profile_id:
                self.profile_list.setCurrentItem(item)
        self.profiles_changed.emit(profiles)

    def _current_profile(self) -> VoiceProfile | None:
        item = self.profile_list.currentItem()
        value = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        return value if isinstance(value, VoiceProfile) else None

    def _selection_changed(self, current: QListWidgetItem | None, _previous: object) -> None:
        enabled = current is not None
        self.rename_button.setEnabled(enabled)
        self.delete_button.setEnabled(enabled)
        self.preview_button.setEnabled(enabled)
        if not enabled:
            self.stop_preview_requested.emit()

    def _play_selected_profile(self) -> None:
        profile = self._current_profile()
        if profile is None:
            return
        self.processing_label.setText("●  Đang tổng hợp câu nghe thử từ đặc điểm giọng...")
        self._set_status("busy")
        self.preview_button.setEnabled(False)
        self.preview_requested.emit(profile)

    def set_preview_state(self, state: str) -> None:
        """Reflect synthesis/playback state for the cloned-voice preview."""

        is_playing = state == "playing"
        is_busy = state in {"synthesizing", "playing"}
        self.preview_button.setText(
            "Đang nghe..." if is_playing else "Nghe thử giọng clone"
        )
        self.preview_button.setEnabled(self._current_profile() is not None and not is_busy)
        self.stop_preview_button.setEnabled(is_playing)
        if state == "playing":
            self.processing_label.setText("●  Đang phát câu nghe thử bằng giọng clone")
            self._set_status("busy")
        elif state == "stopped":
            self.processing_label.setText("●  Đã dừng nghe thử")
            self._set_status("neutral")
        elif state == "ready":
            self.processing_label.setText("●  Giọng clone sẵn sàng")
            self._set_status("success")

    def _refresh_create_button(self) -> None:
        self.create_button.setEnabled(
            not self._enrolling
            and bool(self.name_input.text().strip())
            and self._selected_audio is not None
        )

    def _set_status(self, state: str) -> None:
        self.processing_label.setProperty("state", state)
        self.processing_label.style().unpolish(self.processing_label)
        self.processing_label.style().polish(self.processing_label)
