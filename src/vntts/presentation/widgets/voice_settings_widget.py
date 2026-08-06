"""Voice and future DSP controls."""

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QWidget,
)

from vntts.config.settings import AudioSettings
from vntts.domain.tts.models import AudioEffects, VoiceInfo


class VoiceSettingsWidget(QGroupBox):
    """Collect voice and audio-effect values without applying DSP."""

    def __init__(self, defaults: AudioSettings, parent: QWidget | None = None) -> None:
        super().__init__("Thiết lập giọng", parent)
        self.voice_combo = QComboBox(self)
        self.voice_combo.setObjectName("voiceCombo")
        self.voice_combo.setEnabled(False)

        self.speed_spin = QDoubleSpinBox(self)
        self.speed_spin.setObjectName("speedSpin")
        self.speed_spin.setRange(0.5, 2.0)
        self.speed_spin.setSingleStep(0.1)
        self.speed_spin.setSuffix("x")
        self.speed_spin.setValue(defaults.default_speed)

        self.pitch_spin = QDoubleSpinBox(self)
        self.pitch_spin.setObjectName("pitchSpin")
        self.pitch_spin.setRange(-12.0, 12.0)
        self.pitch_spin.setSingleStep(1.0)
        self.pitch_spin.setSuffix(" semitone")
        self.pitch_spin.setValue(defaults.default_pitch_semitones)

        self.volume_spin = QDoubleSpinBox(self)
        self.volume_spin.setObjectName("volumeSpin")
        self.volume_spin.setRange(-60.0, 12.0)
        self.volume_spin.setSingleStep(1.0)
        self.volume_spin.setSuffix(" dB")
        self.volume_spin.setValue(defaults.default_volume_db)

        layout = QFormLayout(self)
        layout.addRow("Giọng đọc", self.voice_combo)
        layout.addRow("Tốc độ", self.speed_spin)
        layout.addRow("Cao độ", self.pitch_spin)
        layout.addRow("Âm lượng", self.volume_spin)

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
            speed=self.speed_spin.value(),
            pitch_semitones=self.pitch_spin.value(),
            volume_db=self.volume_spin.value(),
        )

