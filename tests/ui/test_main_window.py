"""UI tests for the runnable desktop window."""

from __future__ import annotations

import time
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf
from PySide6.QtCore import QThreadPool, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QBoxLayout,
    QFileDialog,
    QPushButton,
    QScrollArea,
    QStyle,
)

from tests.stubs import StubTTSEngine
from vntts.config.settings import Settings
from vntts.config.theme import build_stylesheet
from vntts.db.models import AudioEffects, HardwareInfo, SynthesisResult
from vntts.engines.factory import EngineFactory, EngineRegistry
from vntts.services.synthesis import SynthesizeSpeech
from vntts.services.voice_profiles import VoiceProfileStore
from vntts.ui.compose_view import DEFAULT_DEMO_TEXT, MainViewModel
from vntts.ui.controls import ChevronComboBox
from vntts.ui.main_window import MainWindow


def _window(qtbot, settings: Settings) -> tuple[MainWindow, MainViewModel]:  # type: ignore[no-untyped-def]
    application = QApplication.instance()
    assert application is not None
    application.setStyle("Fusion")
    application.setStyleSheet(build_stylesheet())
    registry = EngineRegistry()
    registry.register(
        "stub",
        lambda: StubTTSEngine(processing_delay=0.15),
        StubTTSEngine.INFO,
    )
    use_case = SynthesizeSpeech(
        EngineFactory(registry),
        registry,
    )
    voice_store = VoiceProfileStore(settings.paths.data_dir)

    class FakeEnrollmentService:
        def enroll(self, name: str, _source: str):  # type: ignore[no-untyped-def]
            return voice_store.create(
                name,
                np.array([0.1, -0.2], dtype=np.float32),
                np.array([[1, 2, 3]], dtype=np.int64),
                ("Mẫu giọng dài hơn 8 giây; VieNeu chỉ sử dụng 8 giây đầu.",),
            )

    view_model = MainViewModel(
        registry,
        use_case,
        settings,
        hardware=HardwareInfo(
            cpu_name="Test CPU",
            physical_cores=4,
            logical_cores=8,
            ram_gb=8,
            gpu_name=None,
            vram_gb=None,
            cuda_available=False,
            operating_system="Test",
            architecture="x64",
        ),
        thread_pool=QThreadPool(),
        voice_enrollment_service=FakeEnrollmentService(),  # type: ignore[arg-type]
    )
    window = MainWindow(
        view_model,
        settings,
        voice_profile_store=voice_store,
    )
    qtbot.addWidget(window)
    window.show()
    window.start_initialization()
    qtbot.waitUntil(lambda: view_model.state == "idle", timeout=3_000)
    return window, view_model


def test_window_opens(qtbot, settings: Settings) -> None:  # type: ignore[no-untyped-def]
    window, _ = _window(qtbot, settings)

    assert window.isVisible()
    assert window.windowTitle() == settings.application.name
    assert window.text_input.text() == DEFAULT_DEMO_TEXT
    assert window.text_input.character_count.text() == f"{len(DEFAULT_DEMO_TEXT)} ký tự"
    assert window.synthesize_button.text() == "Tạo giọng nói"
    assert window.synthesize_button.isEnabled()
    assert not window.waveform.has_audio


def test_hardware_detection_runs_after_window_is_visible_and_queues_load(
    qtbot,
    settings: Settings,
) -> None:  # type: ignore[no-untyped-def]
    registry = EngineRegistry()
    registry.register("stub", lambda: StubTTSEngine(), StubTTSEngine.INFO)
    use_case = SynthesizeSpeech(EngineFactory(registry), registry)

    def delayed_hardware() -> HardwareInfo:
        time.sleep(0.15)
        return HardwareInfo(
            cpu_name="Test CPU",
            physical_cores=4,
            logical_cores=8,
            ram_gb=8,
            gpu_name=None,
            vram_gb=None,
            cuda_available=False,
            operating_system="Test",
            architecture="x64",
        )

    view_model = MainViewModel(
        registry,
        use_case,
        settings,
        hardware_detector=delayed_hardware,
    )
    window = MainWindow(view_model, settings)
    qtbot.addWidget(window)
    window.show()

    assert window.isVisible()
    assert window.model_settings_page.hardware_label.text() == "Đang kiểm tra phần cứng..."
    assert not window.model_settings_page.load_button.isEnabled()

    window.start_initialization()
    view_model.load_model("stub", "cpu")

    qtbot.waitUntil(lambda: view_model.hardware is not None, timeout=2_000)
    qtbot.waitUntil(lambda: view_model.runtime_info is not None, timeout=2_000)
    assert view_model.selected_engine_id == "stub"
    assert "Không phát hiện CUDA" in window.model_settings_page.hardware_label.text()
    assert window.model_settings_page.load_button.isEnabled()


def test_compose_page_fits_standard_viewport_without_scrolling(
    qtbot, settings: Settings
) -> None:  # type: ignore[no-untyped-def]
    window, _ = _window(qtbot, settings)

    window.resize(1080, 760)
    qtbot.waitUntil(lambda: window.responsive_mode == "wide", timeout=1_000)

    assert window._scroll_area.verticalScrollBar().maximum() == 0
    assert window._scroll_area.horizontalScrollBar().maximum() == 0
    assert window._player_card.isVisible()


def test_sidebar_opens_voice_clone_page_and_creates_profile(
    qtbot, settings: Settings, tmp_path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    window, view_model = _window(qtbot, settings)
    sample = tmp_path / "voice.wav"
    sample_rate = 8_000
    timeline = np.arange(sample_rate * 9, dtype=np.float32) / sample_rate
    sf.write(sample, 0.2 * np.sin(2 * np.pi * 180 * timeline), sample_rate)
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (str(sample), "Audio"),
    )

    window.nav_clone_button.click()
    window.voice_clone_page.name_input.setText("Giọng của tôi")
    window.voice_clone_page.upload_button.click()
    window.voice_clone_page.create_button.click()

    assert window.page_stack.currentIndex() == 1
    assert window.nav_clone_button.isChecked()
    assert window.findChild(QPushButton, "recordVoiceButton") is None
    assert "6–8 giây" in window.voice_clone_page.sample_note.text()
    qtbot.waitUntil(
        lambda: window.voice_clone_page.profile_list.count() == 1,
        timeout=3_000,
    )
    assert window.voice_clone_page.profile_list.count() == 1
    assert "Giọng của tôi" in window.voice_clone_page.profile_list.item(0).text()
    assert "Sẵn sàng" in window.voice_clone_page.profile_list.item(0).text()
    assert "8 giây" in window.voice_clone_page.processing_label.text()
    assert window.voice_clone_page.profile_list.currentItem() is not None
    assert window.voice_clone_page.preview_button.isEnabled()
    synthesis_calls: list[tuple[tuple, dict]] = []
    monkeypatch.setattr(
        view_model,
        "synthesize",
        lambda *args, **kwargs: synthesis_calls.append((args, kwargs)),
    )
    compose_result = SynthesisResult(np.full(120, 0.1, dtype=np.float32), 24_000)
    window._playback.set_audio(compose_result)

    window.voice_clone_page.preview_button.click()

    assert len(synthesis_calls) == 1
    assert synthesis_calls[0][1]["voice_artifact_path"].endswith(".npz")
    assert synthesis_calls[0][1]["engine_id_override"] == "vieneu-v3"
    assert window._playback.current_result is compose_result

    clone_result = SynthesisResult(np.full(80, -0.1, dtype=np.float32), 24_000)
    monkeypatch.setattr(window._clone_playback, "play", lambda: None)
    window._synthesis_completed(clone_result)

    assert window._playback.current_result is compose_result
    assert window._clone_playback.current_result is clone_result

    view_model._selected_engine_id = "vieneu-v3"
    view_model._selected_capabilities = SimpleNamespace(voice_cloning=True)
    window._refresh_voice_choices()
    cloned_index = next(
        index
        for index in range(window.voice_selector.voice_combo.count())
        if str(window.voice_selector.voice_combo.itemData(index)).startswith("clone:")
    )
    window.voice_selector.voice_combo.setCurrentIndex(cloned_index)
    assert window.voice_selector.current_voice_artifact_path() is not None
    synthesis_calls.clear()
    window.text_input.editor.setPlainText("Xin chào bằng giọng đã nhân bản.")

    window._request_synthesis()

    assert synthesis_calls
    assert synthesis_calls[0][1]["voice_artifact_path"].endswith(".npz")


def test_synthesize_button_disabled_for_blank_text(qtbot, settings: Settings) -> None:  # type: ignore[no-untyped-def]
    window, _ = _window(qtbot, settings)

    window.text_input.editor.setPlainText("   ")

    assert not window.synthesize_button.isEnabled()


def test_character_counter_has_no_limit(qtbot, settings: Settings) -> None:  # type: ignore[no-untyped-def]
    window, _ = _window(qtbot, settings)

    window.text_input.editor.setPlainText("a" * 10_001)

    assert window.text_input.character_count.text() == "10.001 ký tự"
    assert window.synthesize_button.isEnabled()


def test_open_file_loads_text_into_editor(
    qtbot, settings: Settings, tmp_path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    window, view_model = _window(qtbot, settings)
    source = tmp_path / "noi-dung.txt"
    source.write_text("Nội dung được nhập từ tệp.", encoding="utf-8")
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (str(source), "Tài liệu hỗ trợ"),
    )

    window.text_input.open_file_button.click()

    qtbot.waitUntil(lambda: view_model.state == "idle", timeout=3_000)
    qtbot.waitUntil(
        lambda: window.text_input.text() == "Nội dung được nhập từ tệp.",
        timeout=3_000,
    )
    assert window.text_input.character_count.text() == "26 ký tự"
    assert "noi-dung.txt" in window.status_label.text()
    assert window.synthesize_button.isEnabled()


@pytest.mark.parametrize(
    ("width", "mode", "workspace_direction", "settings_direction"),
    [
        (1080, "wide", QBoxLayout.Direction.LeftToRight, QBoxLayout.Direction.TopToBottom),
        (820, "compact", QBoxLayout.Direction.TopToBottom, QBoxLayout.Direction.TopToBottom),
        (680, "narrow", QBoxLayout.Direction.TopToBottom, QBoxLayout.Direction.TopToBottom),
    ],
)
def test_layout_reflows_at_responsive_breakpoints(
    qtbot,  # type: ignore[no-untyped-def]
    settings: Settings,
    width: int,
    mode: str,
    workspace_direction: QBoxLayout.Direction,
    settings_direction: QBoxLayout.Direction,
) -> None:
    window, _ = _window(qtbot, settings)

    window.resize(width, 700)
    qtbot.waitUntil(lambda: window.responsive_mode == mode, timeout=1_000)

    assert window._workspace_layout.direction() == workspace_direction
    assert window._settings_layout.direction() == settings_direction
    assert isinstance(window._scroll_area, QScrollArea)
    assert window._scroll_area.widgetResizable()


def test_selecting_engine_updates_voice_list(qtbot, settings: Settings) -> None:  # type: ignore[no-untyped-def]
    window, view_model = _window(qtbot, settings)

    view_model.select_engine("stub")
    qtbot.waitUntil(lambda: window.voice_selector.voice_combo.count() == 3, timeout=3_000)

    assert window.voice_selector.voice_combo.isEnabled()


def test_settings_sections_are_separate_cards(qtbot, settings: Settings) -> None:  # type: ignore[no-untyped-def]
    window, _ = _window(qtbot, settings)

    assert isinstance(window.model_settings_page.model_combo, ChevronComboBox)
    assert isinstance(window.model_settings_page.device_combo, ChevronComboBox)
    assert isinstance(window.voice_selector.voice_combo, ChevronComboBox)
    assert isinstance(window.voice_style.style_combo, ChevronComboBox)
    assert window.model_settings_page.model_combo.maxVisibleItems() == 8
    assert window.voice_selector.voice_combo.maxVisibleItems() == 8
    assert window.voice_style.style_combo.maxVisibleItems() == 8
    assert (
        window.voice_selector.voice_combo.style().styleHint(
            QStyle.StyleHint.SH_ComboBox_Popup
        )
        == 0
    )
    assert window.voice_selector.objectName() == "voiceSelectorCard"
    assert window.voice_selector.title() == "Chọn giọng"
    assert window.voice_style.objectName() == "voiceStyleCard"
    assert window.voice_style.title() == "Phong cách giọng nói"
    assert window.voice_selector.voice_combo.parent() is window.voice_selector
    assert window.voice_style.style_combo.parent() is window.voice_style
    assert window.voice_style.speed_slider.parent() is window.voice_style
    assert [
        window.voice_style.style_combo.itemText(index)
        for index in range(window.voice_style.style_combo.count())
    ] == ["Tự nhiên", "Tin tức", "Kể chuyện"]
    assert window.voice_style.current_style_id() == "tu_nhien"
    assert window.active_model_card.property("card") is True
    assert window.active_model_card.parent() is window._settings_container
    assert window.voice_selector.parent() is window._settings_container
    assert window.voice_style.parent() is window._settings_container
    assert window.voice_style.adjustments_divider.objectName() == "sectionDivider"
    assert window.voice_style.adjustments_divider.height() == 1


def test_model_selection_is_only_on_settings_page(qtbot, settings: Settings) -> None:  # type: ignore[no-untyped-def]
    window, _ = _window(qtbot, settings)

    assert window.page_stack.count() == 3
    assert window.active_model_card.model_label.text() == "Stub TTS Engine"
    assert window.findChild(ChevronComboBox, "engineCombo") is None

    window.nav_settings_button.click()

    assert window.page_stack.currentIndex() == 2
    assert window.nav_settings_button.isChecked()
    assert window.model_settings_page.model_combo.count() == 1
    assert [
        window.model_settings_page.device_combo.itemData(index)
        for index in range(window.model_settings_page.device_combo.count())
    ] == ["auto", "cuda", "cpu"]


def test_style_selection_is_independent_from_voice(
    qtbot, settings: Settings
) -> None:  # type: ignore[no-untyped-def]
    window, _ = _window(qtbot, settings)
    original_voice = window.voice_selector.current_voice_id()

    window.voice_style.style_combo.setCurrentIndex(1)

    assert window.voice_style.current_style_id() == "tin_tuc"
    assert window.voice_selector.current_voice_id() == original_voice


def test_ui_stays_responsive_during_synthesis(qtbot, settings: Settings) -> None:  # type: ignore[no-untyped-def]
    window, view_model = _window(qtbot, settings)
    window.text_input.editor.setPlainText("Đây là kiểm tra worker nền.")
    marker = {"fired": False}

    QTimer.singleShot(20, lambda: marker.__setitem__("fired", True))
    window.synthesize_button.click()

    qtbot.waitUntil(lambda: marker["fired"], timeout=1_000)
    assert view_model.state in {"synthesizing", "completed"}
    qtbot.waitUntil(lambda: view_model.state == "completed", timeout=3_000)
    assert "Hoàn tất" in window.status_label.text()
    assert window.playback_controls.play_button.isEnabled()
    assert not window.playback_controls.stop_button.isEnabled()
    assert window.playback_controls.play_button.accessibleName() == "Phát audio"
    assert window.waveform.has_audio
    assert bool(window.waveform.canvas._envelope.max() > 0)
    assert window.status_label.property("state") == "success"


def test_export_buttons_choose_destination_after_synthesis(
    qtbot, settings: Settings, tmp_path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    window, view_model = _window(qtbot, settings)
    assert not window.export_wav_button.isEnabled()
    assert not window.export_mp3_button.isEnabled()
    window.text_input.editor.setPlainText("Kiểm tra xuất file.")
    window.synthesize_button.click()
    qtbot.waitUntil(lambda: view_model.state == "completed", timeout=3_000)

    destinations = iter((tmp_path / "speech.wav", tmp_path / "speech.mp3"))
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(next(destinations)), "Audio"),
    )
    exported: list[tuple[str, str]] = []
    monkeypatch.setattr(
        window._playback,
        "export_audio",
        lambda path, audio_format: exported.append((path, audio_format)) or tmp_path / path,
    )

    window.export_wav_button.click()
    window.export_mp3_button.click()

    assert exported == [
        (str(tmp_path / "speech.wav"), "wav"),
        (str(tmp_path / "speech.mp3"), "mp3"),
    ]
    assert "speech.mp3" in window.status_label.text()


def test_player_uses_one_button_for_play_and_pause(qtbot, settings: Settings) -> None:  # type: ignore[no-untyped-def]
    window, _ = _window(qtbot, settings)

    window.playback_controls.set_playback_state("playing")

    assert window.playback_controls.play_button.accessibleName() == "Tạm dừng audio"
    assert window.playback_controls.stop_button.isEnabled()

    window.playback_controls.set_playback_state("paused")

    assert window.playback_controls.play_button.accessibleName() == "Phát audio"


def test_closing_window_releases_playback_audio(qtbot, settings: Settings) -> None:  # type: ignore[no-untyped-def]
    window, view_model = _window(qtbot, settings)
    window.text_input.editor.setPlainText("Kiểm tra giải phóng audio.")
    window.synthesize_button.click()
    qtbot.waitUntil(lambda: view_model.state == "completed", timeout=3_000)
    result = window._playback.current_result

    assert result is not None
    assert window._playback.current_wav_bytes is not None
    window.close()
    assert window._playback.current_result is None
    assert window._playback.current_wav_bytes is None


def test_friendly_error_has_no_traceback(qtbot, settings: Settings) -> None:  # type: ignore[no-untyped-def]
    window, view_model = _window(qtbot, settings)

    view_model.synthesize("   ", AudioEffects(), "female-south")
    qtbot.waitUntil(lambda: view_model.state == "error", timeout=1_000)

    assert "Lỗi:" in window.status_label.text()
    assert "Traceback" not in window.status_label.text()
    playback_button = window.findChild(QPushButton, "playButton")
    assert playback_button is not None and not playback_button.isEnabled()
