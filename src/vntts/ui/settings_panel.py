"""Separate voice selection from voice-style adjustment controls."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QLabel,
    QSlider,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from vntts.config.settings import AudioSettings
from vntts.db.models import AudioEffects, SPEECH_STYLE_NAMES, VoiceInfo


class VoiceSelectorWidget(QGroupBox):
    """Present voice selection as a focused, independent card."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Chọn giọng", parent)
        self.setObjectName("voiceSelectorCard")

        helper = QLabel("Chọn chất giọng phù hợp với nội dung của bạn.", self)
        helper.setObjectName("helperText")
        helper.setWordWrap(True)
        helper.hide()
        voice_label = QLabel("Giọng đọc", self)
        voice_label.setObjectName("fieldLabel")
        voice_label.hide()
        self.voice_combo = QComboBox(self)
        self.voice_combo.setObjectName("voiceCombo")
        self.voice_combo.setAccessibleName("Giọng đọc")
        self.voice_combo.setEnabled(False)
        self.voice_combo.setMinimumHeight(38)
        self.voice_combo.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(8)
        layout.addWidget(self.voice_combo)

    def set_voices(
        self,
        voices: list[VoiceInfo],
        reference_audio_paths: dict[str, str] | None = None,
    ) -> None:
        """Replace available voices and enable selection when non-empty."""

        self.voice_combo.clear()
        reference_paths = reference_audio_paths or {}
        for voice in voices:
            self.voice_combo.addItem(voice.display_name, voice.voice_id)
            index = self.voice_combo.count() - 1
            self.voice_combo.setItemData(
                index,
                reference_paths.get(voice.voice_id),
                Qt.ItemDataRole.UserRole + 1,
            )
        self.voice_combo.setEnabled(bool(voices))

    def current_voice_id(self) -> str | None:
        """Return the currently selected voice ID."""

        value = self.voice_combo.currentData()
        return str(value) if value is not None else None

    def current_reference_audio_path(self) -> str | None:
        """Return the reference file paired with the selected cloned voice."""

        value = self.voice_combo.currentData(Qt.ItemDataRole.UserRole + 1)
        return str(value) if value else None


class VoiceStyleWidget(QGroupBox):
    """Select speaking style and collect independent audio adjustments."""

    def __init__(self, defaults: AudioSettings, parent: QWidget | None = None) -> None:
        super().__init__("Phong cách & âm thanh", parent)
        self.setObjectName("voiceStyleCard")

        helper = QLabel("Chọn cách thể hiện mà không thay đổi giọng đã chọn.", self)
        helper.setObjectName("helperText")
        helper.setWordWrap(True)
        helper.hide()

        style_label = QLabel("Phong cách đọc", self)
        style_label.setObjectName("fieldLabel")
        self.style_combo = QComboBox(self)
        self.style_combo.setObjectName("styleCombo")
        self.style_combo.setAccessibleName("Phong cách đọc")
        self.style_combo.setMinimumHeight(38)
        self.style_combo.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )
        self.set_supported_styles(tuple(SPEECH_STYLE_NAMES))

        adjustments_label = QLabel("Tinh chỉnh âm thanh", self)
        adjustments_label.setObjectName("fieldLabel")
        adjustments_label.hide()

        self.speed_slider, self.speed_value = self._slider(
            "Tốc độ",
            5,
            20,
            round(defaults.default_speed * 10),
            lambda value: f"{value / 10:.1f}×",
        )
        self.speed_slider.setObjectName("speedSlider")
        self.pitch_slider, self.pitch_value = self._slider(
            "Cao độ",
            -12,
            12,
            round(defaults.default_pitch_semitones),
            lambda value: f"{value:+d} st",
        )
        self.pitch_slider.setObjectName("pitchSlider")
        self.volume_slider, self.volume_value = self._slider(
            "Âm lượng",
            -60,
            12,
            round(defaults.default_volume_db),
            lambda value: f"{value:+d} dB",
        )
        self.volume_slider.setObjectName("volumeSlider")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(6)
        style_row = QGridLayout()
        style_row.setContentsMargins(0, 0, 0, 0)
        style_row.setHorizontalSpacing(8)
        style_row.addWidget(style_label, 0, 0)
        style_row.addWidget(self.style_combo, 0, 1)
        style_row.setColumnStretch(1, 1)
        layout.addLayout(style_row)
        layout.addLayout(self._slider_row("Tốc độ", self.speed_slider, self.speed_value))
        layout.addLayout(self._slider_row("Cao độ", self.pitch_slider, self.pitch_value))
        layout.addLayout(self._slider_row("Âm lượng", self.volume_slider, self.volume_value))

    def set_supported_styles(self, style_ids: tuple[str, ...]) -> None:
        """Show only styles implemented by the selected engine."""

        selected = self.current_style_id() if hasattr(self, "style_combo") else None
        supported = style_ids or ("tu_nhien",)
        self.style_combo.clear()
        for style_id in supported:
            display_name = SPEECH_STYLE_NAMES.get(
                style_id,
                style_id.replace("_", " ").title(),
            )
            self.style_combo.addItem(display_name, style_id)
        selected_index = self.style_combo.findData(selected)
        self.style_combo.setCurrentIndex(selected_index if selected_index >= 0 else 0)
        has_multiple_styles = self.style_combo.count() > 1
        self.style_combo.setEnabled(has_multiple_styles)
        self.style_combo.setToolTip(
            "Chọn phong cách đọc được hỗ trợ bởi engine."
            if has_multiple_styles
            else "Engine này chỉ hỗ trợ phong cách Tự nhiên."
        )

    def current_style_id(self) -> str:
        """Return the selected engine style identifier."""

        value = self.style_combo.currentData()
        return str(value) if value is not None else "tu_nhien"

    def _divider(self) -> QFrame:
        divider = QFrame(self)
        divider.setObjectName("sectionDivider")
        divider.setFrameShape(QFrame.Shape.NoFrame)
        return divider

    def _slider(
        self,
        name: str,
        minimum: int,
        maximum: int,
        value: int,
        formatter: Callable[[int], str],
    ) -> tuple[QSlider, QLabel]:
        slider = QSlider(Qt.Orientation.Horizontal, self)
        slider.setObjectName(name.replace(" ", "").lower() + "Slider")
        slider.setAccessibleName(name)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        slider.setMinimumHeight(30)
        value_label = QLabel(formatter(value), self)
        value_label.setObjectName("metricValue")
        value_label.setMinimumWidth(56)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        slider.valueChanged.connect(
            lambda current, label=value_label: label.setText(formatter(current))
        )
        return slider, value_label

    def _slider_row(
        self,
        label: str,
        slider: QSlider,
        value_label: QLabel,
    ) -> QGridLayout:
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(0)
        title = QLabel(label, self)
        title.setObjectName("fieldLabel")
        layout.addWidget(title, 0, 0)
        layout.addWidget(slider, 0, 1)
        layout.addWidget(value_label, 0, 2)
        layout.setColumnStretch(1, 1)
        return layout

    def effects(self) -> AudioEffects:
        """Build validated controls for the synthesis request."""

        return AudioEffects(
            speed=self.speed_slider.value() / 10,
            pitch_semitones=float(self.pitch_slider.value()),
            volume_db=float(self.volume_slider.value()),
        )
