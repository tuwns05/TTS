"""Separate voice selection from voice-style adjustment controls."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from vntts.config.settings import AudioSettings
from vntts.config.theme import THEME
from vntts.db.models import (
    SPEECH_STYLE_NAMES,
    AudioEffects,
    EngineInfo,
    EngineRuntimeInfo,
    HardwareInfo,
    VoiceInfo,
)
from vntts.ui.controls import ChevronComboBox


class ActiveModelCard(QFrame):
    """Show only the active state and the hardware used for inference."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("activeModelCard")
        self.setProperty("card", True)
        self.title_label = QLabel("Thiết bị xử lý", self)
        self.title_label.setObjectName("activeModelTitle")
        self.runtime_label = QLabel("Đang kiểm tra phần cứng...", self)
        self.runtime_label.setObjectName("helperText")
        self.runtime_label.setWordWrap(True)
        self._runtime_info: EngineRuntimeInfo | None = None
        self._hardware: HardwareInfo | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(THEME.space_3, THEME.space_3, THEME.space_3, THEME.space_3)
        layout.setSpacing(THEME.space_1)
        layout.addWidget(self.title_label)
        layout.addWidget(self.runtime_label)

    def set_runtime(self, info: EngineRuntimeInfo | None) -> None:
        self._runtime_info = info
        self._refresh_hardware_text()

    def set_hardware(self, hardware: HardwareInfo | None) -> None:
        self._hardware = hardware
        self._refresh_hardware_text()

    def _refresh_hardware_text(self) -> None:
        info = self._runtime_info
        hardware = self._hardware
        if info is None and hardware is None:
            self.runtime_label.setText("Đang kiểm tra phần cứng...")
            return
        if info is not None and info.is_gpu:
            name = info.device_name
            vram = (
                f" · {hardware.vram_gb:.1f} GB VRAM"
                if hardware is not None and hardware.vram_gb is not None
                else ""
            )
            self.runtime_label.setText(f"GPU · {name}{vram}")
            return
        if hardware is not None:
            self.runtime_label.setText(
                f"CPU · {hardware.cpu_name} · {hardware.ram_gb:g} GB RAM"
            )
            return
        self.runtime_label.setText(f"CPU · {info.device_name}")


class ModelSettingsPage(QWidget):
    """Select the processing device used by the packaged speech engine."""

    load_requested = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("modelSettingsPage")
        title = QLabel("Cài đặt thiết bị", self)
        title.setProperty("role", "title")
        intro = QLabel(
            "Chọn thiết bị xử lý dùng để tạo giọng nói. "
            "Khi đổi thiết bị, hệ thống sẽ áp dụng lại cấu hình.",
            self,
        )
        intro.setObjectName("helperText")
        intro.setWordWrap(True)

        card = QFrame(self)
        card.setObjectName("modelSettingsCard")
        card.setProperty("card", True)
        device_label = QLabel("Thiết bị xử lý", card)
        device_label.setObjectName("fieldLabel")
        self.device_combo = ChevronComboBox(card)
        self.device_combo.setObjectName("runtimeDeviceCombo")
        self.device_combo.setAccessibleName("Thiết bị xử lý")
        self.device_combo.addItem("Tự động (khuyến nghị)", "auto")
        self.device_combo.addItem("GPU NVIDIA", "cuda")
        self.device_combo.addItem("CPU", "cpu")
        self.hardware_label = QLabel("Chưa kiểm tra phần cứng.", card)
        self.hardware_label.setObjectName("helperText")
        self.hardware_label.setWordWrap(True)
        self.active_label = QLabel("Chưa có thiết bị đang hoạt động.", card)
        self.active_label.setObjectName("runtimeSummary")
        self.active_label.setWordWrap(True)
        self.load_button = QPushButton("Áp dụng", card)
        self.load_button.setObjectName("loadModelButton")
        self.load_button.setProperty("variant", "primary")
        self.load_button.setEnabled(False)
        self.load_button.clicked.connect(self._emit_load)
        self._selected_engine_id: str | None = None
        self._hardware_ready = False
        self._loading = False
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(THEME.space_4, THEME.space_4, THEME.space_4, THEME.space_4)
        card_layout.setSpacing(THEME.space_2)
        card_layout.addWidget(device_label)
        card_layout.addWidget(self.device_combo)
        card_layout.addWidget(self.hardware_label)
        card_layout.addWidget(self.active_label)
        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(self.load_button)
        card_layout.addLayout(actions)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(THEME.space_5, THEME.space_4, THEME.space_5, THEME.space_5)
        layout.setSpacing(THEME.space_3)
        layout.addWidget(title)
        layout.addWidget(intro)
        layout.addWidget(card)
        layout.addStretch()

    def set_models(self, models: list[EngineInfo], selected_id: str | None) -> None:
        engine_ids = [model.engine_id for model in models]
        self._selected_engine_id = (
            selected_id
            if selected_id in engine_ids
            else engine_ids[0] if engine_ids else None
        )
        self._refresh_load_button_state()

    def set_hardware(self, hardware: HardwareInfo | None, minimum_vram_gb: float | None) -> None:
        self._hardware_ready = hardware is not None
        self._refresh_load_button_state()
        if hardware is None:
            self.hardware_label.setText("Đang kiểm tra phần cứng...")
            return
        if not hardware.cuda_available:
            self.hardware_label.setText(
                "Không phát hiện CUDA. Chế độ Tự động sẽ dùng CPU."
            )
            return
        vram = f"{hardware.vram_gb:.1f} GB VRAM" if hardware.vram_gb is not None else "VRAM không xác định"
        suitable = (
            hardware.vram_gb is not None
            and minimum_vram_gb is not None
            and hardware.vram_gb >= minimum_vram_gb
        )
        suffix = "phù hợp để tự động dùng GPU" if suitable else "không đạt ngưỡng GPU tự động"
        self.hardware_label.setText(f"{hardware.gpu_name} · {vram} · {suffix}.")

    def set_runtime(self, info: EngineRuntimeInfo | None) -> None:
        if info is None:
            self.active_label.setText("Chưa có thiết bị đang hoạt động.")
            return
        if info.is_gpu:
            device = f"GPU · {info.device_name}"
        elif info.device_name.strip().lower() == "cpu":
            device = "CPU"
        else:
            device = f"CPU · {info.device_name}"
        self.active_label.setText(f"Đang hoạt động trên: {device}")

    def set_loading(self, loading: bool) -> None:
        self._loading = loading
        self.device_combo.setEnabled(not loading)
        self._refresh_load_button_state()
        self.load_button.setText("Đang áp dụng..." if loading else "Áp dụng")

    def _emit_load(self) -> None:
        device = self.device_combo.currentData()
        if self._selected_engine_id is not None and device is not None:
            self.load_requested.emit(self._selected_engine_id, str(device))

    def _refresh_load_button_state(self) -> None:
        self.load_button.setEnabled(
            self._hardware_ready
            and self._selected_engine_id is not None
            and not self._loading
        )


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
        self.voice_combo = ChevronComboBox(self)
        self.voice_combo.setObjectName("voiceCombo")
        self.voice_combo.setAccessibleName("Giọng đọc")
        self.voice_combo.setEnabled(False)
        self.voice_combo.setMinimumHeight(THEME.row_height)
        self.voice_combo.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            THEME.space_3,
            THEME.space_4,
            THEME.space_3,
            THEME.space_3,
        )
        layout.setSpacing(THEME.space_2)
        layout.addWidget(self.voice_combo)

    def set_voices(
        self,
        voices: list[VoiceInfo],
        voice_artifact_paths: dict[str, str] | None = None,
    ) -> None:
        """Replace available voices and enable selection when non-empty."""

        self.voice_combo.clear()
        artifact_paths = voice_artifact_paths or {}
        for voice in voices:
            self.voice_combo.addItem(voice.display_name, voice.voice_id)
            index = self.voice_combo.count() - 1
            self.voice_combo.setItemData(
                index,
                artifact_paths.get(voice.voice_id),
                Qt.ItemDataRole.UserRole + 1,
            )
        self.voice_combo.setEnabled(bool(voices))

    def current_voice_id(self) -> str | None:
        """Return the currently selected voice ID."""

        value = self.voice_combo.currentData()
        return str(value) if value is not None else None

    def current_voice_artifact_path(self) -> str | None:
        """Return the numerical feature artifact for a selected cloned voice."""

        value = self.voice_combo.currentData(Qt.ItemDataRole.UserRole + 1)
        return str(value) if value else None


class VoiceStyleWidget(QGroupBox):
    """Select speaking style and collect independent audio adjustments."""

    def __init__(self, defaults: AudioSettings, parent: QWidget | None = None) -> None:
        super().__init__("Phong cách giọng nói", parent)
        self.setObjectName("voiceStyleCard")
        self._defaults = defaults

        self.reset_button = QPushButton("Đặt lại", self)
        self.reset_button.setObjectName("resetVoiceStyleButton")
        self.reset_button.setProperty("variant", "secondary")
        self.reset_button.setAccessibleName(
            "Đặt lại phong cách giọng nói về mặc định"
        )
        self.reset_button.setToolTip(
            "Đặt lại phong cách đọc, tốc độ, cao độ, âm lượng về mặc định"
        )
        self.reset_button.setEnabled(False)

        helper = QLabel("Chọn cách thể hiện mà không thay đổi giọng đã chọn.", self)
        helper.setObjectName("helperText")
        helper.setWordWrap(True)
        helper.hide()

        style_label = QLabel("Phong cách đọc", self)
        style_label.setObjectName("fieldLabel")
        style_label.setProperty("role", "secondary")
        style_label.setFixedWidth(THEME.space_6 * 3 + THEME.space_2)
        self.style_combo = ChevronComboBox(self)
        self.style_combo.setObjectName("styleCombo")
        self.style_combo.setAccessibleName("Phong cách đọc")
        self.style_combo.setMinimumHeight(THEME.row_height)
        self.style_combo.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )
        self.set_supported_styles(tuple(SPEECH_STYLE_NAMES))

        adjustments_label = QLabel("Tinh chỉnh âm thanh", self)
        adjustments_label.setObjectName("fieldLabel")
        adjustments_label.setProperty("role", "secondary")
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
        layout.setContentsMargins(
            THEME.space_3,
            THEME.space_4,
            THEME.space_3,
            THEME.space_3,
        )
        layout.setSpacing(THEME.space_2)
        style_row = QGridLayout()
        style_row.setContentsMargins(0, 0, 0, 0)
        style_row.setHorizontalSpacing(THEME.space_2)
        style_row.addWidget(style_label, 0, 0)
        style_row.addWidget(self.style_combo, 0, 1)
        style_row.setColumnStretch(1, 1)
        layout.addLayout(style_row)
        self.adjustments_divider = QFrame(self)
        self.adjustments_divider.setObjectName("sectionDivider")
        self.adjustments_divider.setFrameShape(QFrame.Shape.NoFrame)
        self.adjustments_divider.setFixedHeight(1)
        layout.addWidget(self.adjustments_divider)
        sliders = QGridLayout()
        sliders.setContentsMargins(0, 0, 0, 0)
        sliders.setHorizontalSpacing(THEME.space_2)
        sliders.setVerticalSpacing(THEME.space_1)
        self._add_slider_row(sliders, 0, "Tốc độ", self.speed_slider, self.speed_value)
        self._add_slider_row(sliders, 1, "Cao độ", self.pitch_slider, self.pitch_value)
        self._add_slider_row(
            sliders,
            2,
            "Âm lượng",
            self.volume_slider,
            self.volume_value,
        )
        sliders.setColumnStretch(1, 1)
        layout.addLayout(sliders)
        reset_row = QHBoxLayout()
        reset_row.setContentsMargins(0, 0, 0, 0)
        reset_row.addStretch()
        reset_row.addWidget(self.reset_button)
        layout.addLayout(reset_row)

        self.style_combo.currentIndexChanged.connect(
            self._refresh_reset_button_state
        )
        self.speed_slider.valueChanged.connect(self._refresh_reset_button_state)
        self.pitch_slider.valueChanged.connect(self._refresh_reset_button_state)
        self.volume_slider.valueChanged.connect(self._refresh_reset_button_state)
        self.reset_button.clicked.connect(self._reset_to_defaults)

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
        self.style_combo.setCurrentIndex(max(selected_index, 0))
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

    def _reset_to_defaults(self) -> None:
        default_style_index = self.style_combo.findData("tu_nhien")
        if default_style_index >= 0:
            self.style_combo.setCurrentIndex(default_style_index)
        self.speed_slider.setValue(round(self._defaults.default_speed * 10))
        self.pitch_slider.setValue(round(self._defaults.default_pitch_semitones))
        self.volume_slider.setValue(round(self._defaults.default_volume_db))
        self._refresh_reset_button_state()

    def _refresh_reset_button_state(self) -> None:
        is_dirty = (
            self.current_style_id() != "tu_nhien"
            or self.speed_slider.value()
            != round(self._defaults.default_speed * 10)
            or self.pitch_slider.value()
            != round(self._defaults.default_pitch_semitones)
            or self.volume_slider.value()
            != round(self._defaults.default_volume_db)
        )
        self.reset_button.setEnabled(is_dirty)

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
        slider.setMinimumHeight(THEME.space_4 + THEME.space_1)
        value_label = QLabel(formatter(value), self)
        value_label.setObjectName("metricValue")
        value_label.setFixedWidth(THEME.space_6 + THEME.space_4)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        slider.valueChanged.connect(
            lambda current, label=value_label: label.setText(formatter(current))
        )
        return slider, value_label

    def _add_slider_row(
        self,
        layout: QGridLayout,
        row: int,
        label: str,
        slider: QSlider,
        value_label: QLabel,
    ) -> None:
        title = QLabel(label, self)
        title.setObjectName("fieldLabel")
        title.setProperty("role", "secondary")
        title.setFixedWidth(THEME.space_6 * 2)
        layout.addWidget(title, row, 0)
        layout.addWidget(slider, row, 1)
        layout.addWidget(value_label, row, 2)

    def effects(self) -> AudioEffects:
        """Build validated controls for the synthesis request."""

        return AudioEffects(
            speed=self.speed_slider.value() / 10,
            pitch_semitones=float(self.pitch_slider.value()),
            volume_db=float(self.volume_slider.value()),
        )
