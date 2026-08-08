"""UI tests for the runnable desktop window."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QThreadPool, QTimer
from PySide6.QtWidgets import QBoxLayout, QFileDialog, QPushButton, QScrollArea

from vntts.engines.factory import EngineFactory, EngineRegistry
from vntts.config.settings import Settings
from vntts.db.models import AudioEffects
from vntts.services.synthesis import SynthesizeSpeech
from vntts.ui.compose_view import MainViewModel
from vntts.ui.main_window import MainWindow
from tests.stubs import StubTTSEngine


def _window(qtbot, settings: Settings) -> tuple[MainWindow, MainViewModel]:  # type: ignore[no-untyped-def]
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
    view_model = MainViewModel(
        registry,
        use_case,
        settings,
        thread_pool=QThreadPool(),
    )
    window = MainWindow(view_model, settings)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: view_model.state == "idle", timeout=3_000)
    return window, view_model


def test_window_opens(qtbot, settings: Settings) -> None:  # type: ignore[no-untyped-def]
    window, _ = _window(qtbot, settings)

    assert window.isVisible()
    assert window.windowTitle() == settings.application.name
    assert window.synthesize_button.text() == "Tạo giọng nói"
    assert not window.waveform.has_audio


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
        (820, "compact", QBoxLayout.Direction.TopToBottom, QBoxLayout.Direction.LeftToRight),
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
    assert isinstance(window.centralWidget(), QScrollArea)
    assert window._scroll_area.widgetResizable()


def test_selecting_engine_updates_voice_list(qtbot, settings: Settings) -> None:  # type: ignore[no-untyped-def]
    window, view_model = _window(qtbot, settings)

    view_model.select_engine("stub")
    qtbot.waitUntil(lambda: window.voice_selector.voice_combo.count() == 3, timeout=3_000)

    assert window.voice_selector.voice_combo.isEnabled()


def test_voice_and_style_are_separate_cards(qtbot, settings: Settings) -> None:  # type: ignore[no-untyped-def]
    window, _ = _window(qtbot, settings)

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
