"""UI tests for the runnable Phase 1 window."""

from __future__ import annotations

from PySide6.QtCore import QThreadPool, QTimer
from PySide6.QtWidgets import QPushButton

from vntts.application.services.engine_factory import EngineFactory
from vntts.application.services.engine_registry import EngineRegistry
from vntts.application.use_cases.synthesize_speech import SynthesizeSpeech
from vntts.config.settings import Settings
from vntts.domain.tts.models import AudioEffects
from vntts.infrastructure.engines.fake_engine import FakeTTSEngine
from vntts.presentation.main_window import MainWindow
from vntts.presentation.viewmodels.main_viewmodel import MainViewModel


def _window(qtbot, settings: Settings) -> tuple[MainWindow, MainViewModel]:  # type: ignore[no-untyped-def]
    registry = EngineRegistry()
    registry.register(
        "fake",
        lambda: FakeTTSEngine(processing_delay=0.15),
        FakeTTSEngine.INFO,
    )
    use_case = SynthesizeSpeech(
        EngineFactory(registry),
        registry,
        settings.tts.max_text_length,
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


def test_synthesize_button_disabled_for_blank_text(qtbot, settings: Settings) -> None:  # type: ignore[no-untyped-def]
    window, _ = _window(qtbot, settings)

    window.text_input.editor.setPlainText("   ")

    assert not window.synthesize_button.isEnabled()


def test_selecting_engine_updates_voice_list(qtbot, settings: Settings) -> None:  # type: ignore[no-untyped-def]
    window, view_model = _window(qtbot, settings)

    view_model.select_engine("fake")
    qtbot.waitUntil(lambda: window.voice_settings.voice_combo.count() == 3, timeout=3_000)

    assert window.voice_settings.voice_combo.isEnabled()


def test_ui_stays_responsive_during_fake_synthesis(qtbot, settings: Settings) -> None:  # type: ignore[no-untyped-def]
    window, view_model = _window(qtbot, settings)
    window.text_input.editor.setPlainText("Đây là kiểm tra worker nền.")
    marker = {"fired": False}

    QTimer.singleShot(20, lambda: marker.__setitem__("fired", True))
    window.synthesize_button.click()

    qtbot.waitUntil(lambda: marker["fired"], timeout=1_000)
    assert view_model.state in {"synthesizing", "completed"}
    qtbot.waitUntil(lambda: view_model.state == "completed", timeout=3_000)
    assert "Hoàn tất" in window.status_label.text()


def test_friendly_error_has_no_traceback(qtbot, settings: Settings) -> None:  # type: ignore[no-untyped-def]
    window, view_model = _window(qtbot, settings)

    view_model.synthesize("   ", AudioEffects(), "female-south")
    qtbot.waitUntil(lambda: view_model.state == "error", timeout=1_000)

    assert "Lỗi:" in window.status_label.text()
    assert "Traceback" not in window.status_label.text()
    playback_button = window.findChild(QPushButton, "playButton")
    assert playback_button is not None and not playback_button.isEnabled()
