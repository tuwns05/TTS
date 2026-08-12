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
    """Read-only summary of the model loaded from the Settings page."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("activeModelCard")
        self.setProperty("card", True)
        title = QLabel("Model đang hoạt động", self)
        title.setProperty("role", "section")
        self.model_label = QLabel("Chưa load model", self)
        self.model_label.setObjectName("activeModelName")
        self.runtime_label = QLabel("Mở Cài đặt để chọn model và thiết bị.", self)
        self.runtime_label.setObjectName("helperText")
        self.runtime_label.setWordWrap(True)
        self.status_badge = QLabel("Đang chờ", self)
        self.status_badge.setObjectName("engineStatus")
        self.status_badge.setProperty("state", "neutral")
        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.status_badge)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(THEME.space_3, THEME.space_3, THEME.space_3, THEME.space_3)
        layout.setSpacing(THEME.space_1)
        layout.addLayout(header)
        layout.addWidget(self.model_label)
        layout.addWidget(self.runtime_label)

    def set_runtime(self, info: EngineRuntimeInfo | None) -> None:
        if info is None:
            self.model_label.setText("Chưa load model")
            self.runtime_label.setText("Mở Cài đặt để chọn model và thiết bị.")
            return
        self.model_label.setText(info.display_name)
        backend = "PyTorch" if info.backend == "pytorch" else info.backend.upper()
        target = f"GPU · {info.device_name}" if info.is_gpu else "CPU"
        details = f"{target} · {backend}"
        if info.fallback_reason:
            details += f"\n{info.fallback_reason}"
        self.runtime_label.setText(details)

    def set_status(self, text: str, state: str) -> None:
        self.status_badge.setText(text)
        self.status_badge.setProperty("state", state)
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)


class ModelSettingsPage(QWidget):
    """Select a packaged model and explicitly load it on CPU, GPU, or auto."""

    load_requested = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("modelSettingsPage")
        title = QLabel("Cài đặt model", self)
        title.setProperty("role", "title")
        intro = QLabel(
            "Chọn model đã được đóng gói và thiết bị suy luận. "
            "Khi đổi thiết bị, model sẽ được load lại.",
            self,
        )
        intro.setObjectName("helperText")
        intro.setWordWrap(True)

        card = QFrame(self)
        card.setObjectName("modelSettingsCard")
        card.setProperty("card", True)
        model_label = QLabel("Model đóng gói", card)
        model_label.setObjectName("fieldLabel")
        self.model_combo = ChevronComboBox(card)
        self.model_combo.setObjectName("packagedModelCombo")
        self.model_combo.setAccessibleName("Model đóng gói")
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
        self.active_label = QLabel("Chưa load model.", card)
        self.active_label.setObjectName("runtimeSummary")
        self.active_label.setWordWrap(True)
        self.load_button = QPushButton("Load model", card)
        self.load_button.setObjectName("loadModelButton")
        self.load_button.setProperty("variant", "primary")
        self.load_button.clicked.connect(self._emit_load)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(THEME.space_4, THEME.space_4, THEME.space_4, THEME.space_4)
        card_layout.setSpacing(THEME.space_2)
        card_layout.addWidget(model_label)
        card_layout.addWidget(self.model_combo)
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
        self.model_combo.clear()
        selected_index = 0
        for index, model in enumerate(models):
            self.model_combo.addItem(model.display_name, model.engine_id)
            if model.engine_id == selected_id:
                selected_index = index
        if self.model_combo.count():
            self.model_combo.setCurrentIndex(selected_index)

    def set_hardware(self, hardware: HardwareInfo | None, minimum_vram_gb: float | None) -> None:
        if hardware is None or not hardware.cuda_available:
            self.hardware_label.setText(
                "Không phát hiện CUDA. Chế độ Tự động sẽ dùng CPU/ONNX."
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
            self.active_label.setText("Chưa load model.")
            return
        details = f"Đang hoạt động: {info.summary}"
        if info.fallback_reason:
            details += f"\n{info.fallback_reason}"
        self.active_label.setText(details)

    def set_loading(self, loading: bool) -> None:
        self.model_combo.setEnabled(not loading)
        self.device_combo.setEnabled(not loading)
        self.load_button.setEnabled(not loading)
        self.load_button.setText("Đang load..." if loading else "Load model")

    def _emit_load(self) -> None:
        engine_id = self.model_combo.currentData()
        device = self.device_combo.currentData()
        if engine_id is not None and device is not None:
            self.load_requested.emit(str(engine_id), str(device))


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

        helper = QLabel("Chọn cách thể hiện mà không thay đổi giọng đã chọn.", self)
        helper.setObjectName("helperText")
        helper.setWordWrap(True)
        helper.hide()

        style_label = QLabel("Phong cách đọc", self)
        style_label.setObjectName("fieldLabel")
        style_label.setProperty("role", "secondary")
        style_label.setFixedWidth(THEME.space_6 * 3)
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
