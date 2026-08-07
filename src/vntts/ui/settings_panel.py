"""Voice selection and compact audio adjustment controls."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from vntts.config.settings import AudioSettings
from vntts.db.models import AudioEffects, VoiceInfo


class VoiceSettingsWidget(QGroupBox):
    """Collect voice and audio-effect values in an accessible card."""

    def __init__(self, defaults: AudioSettings, parent: QWidget | None = None) -> None:
        super().__init__("Thiết lập giọng", parent)
        self.setObjectName("voiceSettingsCard")

        voice_label = QLabel("Giọng đọc", self)
        voice_label.setObjectName("fieldLabel")
        self.voice_combo = QComboBox(self)
        self.voice_combo.setObjectName("voiceCombo")
        self.voice_combo.setAccessibleName("Giọng đọc")
        self.voice_combo.setEnabled(False)
        self.voice_combo.setMinimumHeight(44)

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
        layout.setContentsMargins(16, 24, 16, 16)
        layout.setSpacing(8)
        layout.addWidget(voice_label)
        layout.addWidget(self.voice_combo)
        layout.addSpacing(8)
        layout.addLayout(
            self._slider_row("Tốc độ", self.speed_slider, self.speed_value)
        )
        layout.addLayout(
            self._slider_row("Cao độ", self.pitch_slider, self.pitch_value)
        )
        layout.addLayout(
            self._slider_row("Âm lượng", self.volume_slider, self.volume_value)
        )

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
        slider.setMinimumHeight(44)
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
        layout.addWidget(value_label, 0, 1)
        layout.addWidget(slider, 1, 0, 1, 2)
        return layout

    def set_voices(self, voices: list[VoiceInfo]) -> None:
        """Replace available voices and enable selection when non-empty."""

        self.voice_combo.clear()
        for voice in voices:
            self.voice_combo.addItem(voice.display_name, voice.voice_id)
        self.voice_combo.setEnabled(bool(voices))

    def current_voice_id(self) -> str | None:
        """Return the currently selected voice ID."""

        value = self.voice_combo.currentData()
        return str(value) if value is not None else None

    def effects(self) -> AudioEffects:
        """Build validated controls for the synthesis request."""

        return AudioEffects(
            speed=self.speed_slider.value() / 10,
            pitch_semitones=float(self.pitch_slider.value()),
            volume_db=float(self.volume_slider.value()),
        )
