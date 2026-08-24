"""UI tests for the runnable desktop window."""

from __future__ import annotations

import time
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf
from PySide6.QtCore import Qt, QThreadPool, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QBoxLayout,
    QFileDialog,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QToolButton,
)

from tests.stubs import StubTTSEngine
from vntts.config.settings import Settings
from vntts.config.theme import THEME, build_stylesheet
from vntts.db.models import AudioEffects, HardwareInfo, SynthesisResult
from vntts.engines.factory import EngineFactory, EngineRegistry
from vntts.services.license_service import (
    LICENSE_REQUIRED_MESSAGE,
    LicenseActivationResult,
    LicenseStatus,
)
from vntts.services.payment_service import PaymentResponse
from vntts.services.synthesis import SynthesizeSpeech
from vntts.services.voice_profiles import VoiceProfileStore
from vntts.ui.compose_view import DEFAULT_DEMO_TEXT, MainViewModel
from vntts.ui.controls import ChevronComboBox
from vntts.ui.main_window import MainWindow


class LicensedTestService:
    """Keep unrelated UI tests focused on their original licensed workflow."""

    def __init__(self) -> None:
        self.result = LicenseActivationResult(
            activated=True,
            message="Xác thực mã kích hoạt thành công.",
            customer_name="Test Customer",
            plan="yearly",
            paid_at="2026-08-19T14:48:00+07:00",
            expires_at="2027-08-19T14:48:00+07:00",
            mac="F0:68:E3:C4:D1:A1",
        )

    def saved_key(self) -> str | None:
        return "TEST-LICENSE-KEY"

    def validate_saved(self) -> LicenseActivationResult:
        return self.result

    def activate(self, _key: str) -> LicenseActivationResult:
        return self.result


def _window(
    qtbot,
    settings: Settings,
    *,
    payment_service=None,  # type: ignore[no-untyped-def]
    license_service=None,  # type: ignore[no-untyped-def]
) -> tuple[MainWindow, MainViewModel]:  # type: ignore[no-untyped-def]
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
        payment_service=payment_service,
        license_service=license_service or LicensedTestService(),
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
    assert window.sidebar_brand.alignment() == Qt.AlignmentFlag.AlignCenter
    assert window.sidebar_brand.font().pixelSize() == THEME.font_size_section + 1
    assert window.sidebar_tagline.text() == "Chuyển văn bản thành giọng nói"
    assert window.sidebar_tagline.alignment() == Qt.AlignmentFlag.AlignCenter
    assert window.sidebar_tagline.wordWrap()
    assert window.sidebar_brand_divider.height() == max(
        1, int(THEME.control_stroke_width)
    )
    assert window.text_input.text() == DEFAULT_DEMO_TEXT
    assert window.text_input.character_count.text() == f"{len(DEFAULT_DEMO_TEXT)} ký tự"
    assert window.synthesize_button.text() == "Tạo giọng nói"
    assert window.synthesize_button.isEnabled()
    assert not window.waveform.has_audio


def test_unlicensed_startup_locks_feature_pages_and_redirects_to_payment(
    qtbot,
    settings: Settings,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    class UnlicensedService:
        def saved_key(self) -> str | None:
            return None

        def validate_saved(self) -> LicenseActivationResult:
            return LicenseActivationResult(
                activated=False,
                message=LICENSE_REQUIRED_MESSAGE,
                status=LicenseStatus.NOT_ACTIVATED,
            )

    window, _ = _window(
        qtbot,
        settings,
        license_service=UnlicensedService(),  # type: ignore[arg-type]
    )
    notifications: list[str] = []
    monkeypatch.setattr(window, "_show_license_notification", notifications.append)

    assert window.page_stack.currentIndex() == 3
    assert window.nav_compose_button.license_locked
    assert window.nav_clone_button.license_locked
    assert window.nav_compose_button.property("licenseLocked") is True
    assert window.nav_clone_button.property("licenseLocked") is True
    assert not window.synthesize_button.isEnabled()

    window.nav_clone_button.click()

    assert window.page_stack.currentIndex() == 3
    assert notifications == [LICENSE_REQUIRED_MESSAGE]


def test_license_expiring_while_open_blocks_next_synthesis(
    qtbot,
    settings: Settings,
) -> None:  # type: ignore[no-untyped-def]
    license_service = LicensedTestService()
    window, view_model = _window(
        qtbot,
        settings,
        license_service=license_service,
    )
    assert window.synthesize_button.isEnabled()
    license_service.result = LicenseActivationResult(
        activated=False,
        message="Mã kích hoạt đã hết hạn.",
        status=LicenseStatus.EXPIRED,
    )

    window.synthesize_button.click()

    assert view_model.state == "idle"
    assert window.page_stack.currentIndex() == 3
    assert window.nav_compose_button.license_locked
    assert window.nav_clone_button.license_locked
    assert window.payment_page.license_status_label.text() == (
        "Mã kích hoạt đã hết hạn."
    )


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


def test_compose_and_payment_help_buttons_open_contextual_guides(
    qtbot, settings: Settings, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    window, _ = _window(qtbot, settings)
    opened_guides: list[tuple[str, str]] = []

    def capture_guide(_parent, title, message, *_args, **_kwargs):  # type: ignore[no-untyped-def]
        opened_guides.append((title, message))
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "information", capture_guide)

    assert window.compose_help_button.text() == "Hướng dẫn"
    assert window.compose_help_button.property("variant") == "help"
    assert window.compose_help_button.maximumHeight() <= 32
    window.compose_help_button.click()

    window.nav_payment_button.click()
    assert window.payment_page.payment_help_button.text() == "Hướng dẫn"
    assert window.payment_page.payment_help_button.property("variant") == "help"
    assert window.payment_page.payment_help_button.maximumHeight() <= 32
    window.payment_page.payment_help_button.click()

    assert len(opened_guides) == 2
    assert opened_guides[0][0] == "Hướng dẫn tạo giọng nói"
    assert "Mở tệp" in opened_guides[0][1]
    assert "Xuất WAV" in opened_guides[0][1]
    assert opened_guides[1][0] == "Hướng dẫn thanh toán và kích hoạt"
    assert "Gửi yêu cầu thanh toán" in opened_guides[1][1]
    assert "Mã kích hoạt" in opened_guides[1][1]
    assert "MAC" not in opened_guides[1][1]


def test_voice_clone_selected_file_can_be_cleared(
    qtbot, settings: Settings, tmp_path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    window, _ = _window(qtbot, settings)
    sample = tmp_path / "voice.mp3"
    sample.write_bytes(b"sample")
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (str(sample), "Audio"),
    )

    page = window.voice_clone_page
    page.name_input.setText("Giọng thử")
    page.upload_button.click()

    assert page.audio_label.text() == "voice.mp3"
    assert not page.audio_file_card.isHidden()
    assert page.audio_meta_label.text() == "Mẫu giọng đã sẵn sàng"
    assert page.upload_button.text() == "Thay đổi"
    assert page.audio_file_card.property("hasFile") is True
    assert page.clear_audio_button.text() == "Xóa"
    assert page.clear_audio_button.icon().isNull()
    assert not page.clear_audio_button.isHidden()
    assert page.clear_audio_button.isEnabled()
    assert page.create_button.isEnabled()

    page.clear_audio_button.click()

    assert page.audio_label.text() == "Chưa chọn mẫu giọng"
    assert not page.audio_file_card.isHidden()
    assert "WAV, MP3, FLAC" in page.audio_meta_label.text()
    assert page.upload_button.text() == "Chọn file"
    assert page.audio_file_card.property("hasFile") is False
    assert page.clear_audio_button.isHidden()
    assert "Chờ mẫu giọng" in page.processing_label.text()
    assert not page.clear_audio_button.isEnabled()
    assert not page.create_button.isEnabled()
    assert sample.is_file()


def test_voice_clone_empty_state_and_responsive_layout(
    qtbot, settings: Settings
) -> None:  # type: ignore[no-untyped-def]
    window, _ = _window(qtbot, settings)
    page = window.voice_clone_page
    window.nav_clone_button.click()

    assert not page.empty_profiles.isHidden()
    assert page.profile_list.isHidden()
    assert page.profile_count_label.text() == "0 hồ sơ"
    assert page.create_button.property("variant") == "primary"
    assert page._form_footer.indexOf(page.processing_label) >= 0
    assert page._form_footer.indexOf(page.create_button) >= 0

    window.resize(760, 700)
    qtbot.waitUntil(lambda: page._responsive_mode == "narrow", timeout=1_000)
    assert window._clone_scroll_area.horizontalScrollBar().maximum() == 0
    assert page._file_selector_layout.direction() == QBoxLayout.Direction.TopToBottom
    assert page._form_footer.direction() == QBoxLayout.Direction.TopToBottom

    window.resize(1180, 760)
    qtbot.waitUntil(lambda: page._responsive_mode == "wide", timeout=1_000)
    assert page._file_selector_layout.direction() == QBoxLayout.Direction.LeftToRight
    assert page._form_footer.direction() == QBoxLayout.Direction.LeftToRight


def test_voice_clone_enrollment_busy_and_error_states(
    qtbot, settings: Settings, tmp_path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    window, _ = _window(qtbot, settings)
    page = window.voice_clone_page
    sample = tmp_path / "voice.wav"
    sample.write_bytes(b"sample")
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (str(sample), "Audio"),
    )

    page.name_input.setText("Giọng thử")
    page.upload_button.click()
    page.create_button.click()

    assert page._enrolling
    assert "Đang tạo hồ sơ" in page.processing_label.text()
    assert page.processing_label.property("state") == "busy"
    assert not page.name_input.isEnabled()
    assert not page.upload_button.isEnabled()
    assert not page.create_button.isEnabled()

    page.enrollment_failed("Mẫu âm thanh không hợp lệ")

    assert not page._enrolling
    assert "Mẫu âm thanh không hợp lệ" in page.processing_label.text()
    assert page.processing_label.property("state") == "error"
    assert page.name_input.isEnabled()
    assert page.upload_button.isEnabled()
    assert page.create_button.isEnabled()


def test_voice_profile_preview_and_overflow_actions(
    qtbot, settings: Settings, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    window, _ = _window(qtbot, settings)
    page = window.voice_clone_page
    profile = page._store.create(
        "Giọng ban đầu",
        np.array([0.1], dtype=np.float32),
        np.array([[1]], dtype=np.int64),
    )
    page._reload_profiles(profile.profile_id)
    previewed: list[object] = []
    stopped: list[bool] = []
    page.preview_requested.connect(previewed.append)
    page.stop_preview_requested.connect(lambda: stopped.append(True))

    page.preview_button.click()
    assert previewed == [profile]
    assert page.preview_button.text() == "Đang tạo..."
    page.set_preview_state("playing")
    assert page.preview_button.text() == "Dừng"
    assert page.preview_button.isEnabled()
    page.preview_button.click()
    assert stopped
    page.set_preview_state("stopped")
    assert page.preview_button.text() == "Nghe thử"

    monkeypatch.setattr(
        QInputDialog,
        "getText",
        lambda *args, **kwargs: ("Giọng đã đổi tên", True),
    )
    row = page.profile_list.itemWidget(page.profile_list.item(0))
    menu = row.findChild(QToolButton, "voiceProfileMenuButton").menu()
    menu.actions()[0].trigger()
    renamed_row = page.profile_list.itemWidget(page.profile_list.item(0))
    assert "Giọng đã đổi tên" in renamed_row.findChild(
        QLabel, "voiceProfileRowName"
    ).text()

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    renamed_menu = renamed_row.findChild(QToolButton, "voiceProfileMenuButton").menu()
    renamed_menu.actions()[-1].trigger()
    assert page.profile_list.count() == 0
    assert not page.empty_profiles.isHidden()


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
    profile_row = window.voice_clone_page.profile_list.itemWidget(
        window.voice_clone_page.profile_list.item(0)
    )
    assert profile_row is not None
    profile_name = profile_row.findChild(QLabel, "voiceProfileRowName")
    profile_state = profile_row.findChild(QLabel, "voiceProfileState")
    assert profile_name is not None
    assert profile_state is not None
    assert "Giọng của tôi" in profile_name.text()
    assert "Sẵn sàng" in profile_state.text()
    assert window.voice_clone_page.profile_list.item(0).text() == ""
    assert (
        window.voice_clone_page.profile_list.item(0).sizeHint().height()
        == THEME.clone_profile_row_height
    )
    assert profile_row.findChild(QPushButton, "renameVoiceProfileButton") is None
    assert profile_row.findChild(QPushButton, "deleteVoiceProfileButton") is None
    preview_button = profile_row.findChild(QPushButton, "previewVoiceProfileButton")
    more_button = profile_row.findChild(QToolButton, "voiceProfileMenuButton")
    assert preview_button is not None
    assert more_button is not None
    assert preview_button.text() == "Nghe thử"
    assert more_button.text() == "⋮"
    assert more_button.icon().isNull()
    assert isinstance(more_button.menu(), QMenu)
    assert [action.text() for action in more_button.menu().actions()] == [
        "Đổi tên",
        "",
        "Xóa hồ sơ",
    ]
    assert window.voice_clone_page.profile_count_label.text() == "1 hồ sơ"
    assert window.voice_clone_page.empty_profiles.isHidden()
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
    assert window.voice_clone_page.preview_button.text() == "Đang tạo..."
    assert not window.voice_clone_page.preview_button.isEnabled()
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

    assert isinstance(window.model_settings_page.device_combo, ChevronComboBox)
    assert isinstance(window.voice_selector.voice_combo, ChevronComboBox)
    assert isinstance(window.voice_style.style_combo, ChevronComboBox)
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
    assert window.voice_style.reset_button.text() == "Đặt lại"
    assert window.voice_style.reset_button.property("variant") == "secondary"
    assert (
        window.voice_style.reset_button.geometry().top()
        > window.voice_style.volume_slider.geometry().bottom()
    )
    assert (
        window.voice_style.reset_button.geometry().center().x()
        > window.voice_style.style_combo.geometry().center().x()
    )
    assert window.voice_selector.voice_combo.parent() is window.voice_selector
    assert window.voice_style.style_combo.parent() is window.voice_style
    assert window.voice_style.speed_slider.parent() is window.voice_style
    assert [
        window.voice_style.style_combo.itemText(index)
        for index in range(window.voice_style.style_combo.count())
    ] == ["Tự nhiên", "Tin tức", "Kể chuyện"]
    assert window.voice_style.current_style_id() == "tu_nhien"
    style_label = next(
        label
        for label in window.voice_style.findChildren(QLabel, "fieldLabel")
        if label.text() == "Phong cách đọc"
    )
    assert style_label.width() == THEME.space_6 * 3 + THEME.space_2
    assert window.active_model_card.property("card") is True
    assert window.active_model_card.parent() is window._settings_container
    assert window.voice_selector.parent() is window._settings_container
    assert window.voice_style.parent() is window._settings_container
    assert window.voice_style.adjustments_divider.objectName() == "sectionDivider"
    assert window.voice_style.adjustments_divider.height() == 1


def test_settings_page_only_exposes_device_selection(qtbot, settings: Settings) -> None:  # type: ignore[no-untyped-def]
    window, _ = _window(qtbot, settings)

    assert window.page_stack.count() == 5
    assert window.active_model_card.title_label.text() == "Thiết bị xử lý"
    assert window.active_model_card.title_label.objectName() == "activeModelTitle"
    assert window.active_model_card.title_label.font().bold()
    assert (
        window.active_model_card.title_label.palette().windowText().color().name()
        == THEME.success.lower()
    )
    assert window.active_model_card.runtime_label.text() == "CPU · Test CPU · 8 GB RAM"
    assert window.active_model_card.findChild(QLabel, "activeModelName") is None
    assert window.active_model_card.findChild(QLabel, "engineStatus") is None
    assert window.findChild(ChevronComboBox, "engineCombo") is None

    window.nav_settings_button.click()

    assert window.page_stack.currentIndex() == 2
    assert window.nav_settings_button.isChecked()
    assert window.findChild(ChevronComboBox, "packagedModelCombo") is None
    assert window.model_settings_page.load_button.text() == "Áp dụng"
    assert (
        window.model_settings_page.active_label.text()
        == "Đang hoạt động trên: CPU"
    )
    assert "Stub TTS Engine" not in window.model_settings_page.active_label.text()
    assert [
        window.model_settings_page.device_combo.itemData(index)
        for index in range(window.model_settings_page.device_combo.count())
    ] == ["auto", "cuda", "cpu"]


def test_payment_page_validates_and_uses_separate_services(
    qtbot,
    settings: Settings,
) -> None:  # type: ignore[no-untyped-def]
    class RecordingPaymentService:
        def __init__(self) -> None:
            self.requests = []

        def request_payment(self, payment):  # type: ignore[no-untyped-def]
            time.sleep(0.05)
            self.requests.append(payment)
            return PaymentResponse(
                accepted=True,
                message=(
                    "Yêu cầu thanh toán đã được gửi.\n"
                    "Vui lòng kiểm tra email để nhận hướng dẫn thanh toán."
                ),
                mocked=True,
            )

    class RecordingLicenseService:
        def __init__(self) -> None:
            self.keys: list[str] = []

        def saved_key(self) -> str | None:
            return None

        def validate_saved(self) -> LicenseActivationResult:
            return LicenseActivationResult(
                activated=False,
                message=LICENSE_REQUIRED_MESSAGE,
                status=LicenseStatus.NOT_ACTIVATED,
            )

        def activate(self, key: str) -> LicenseActivationResult:
            self.keys.append(key)
            return LicenseActivationResult(
                activated=True,
                message="Xác thực mã kích hoạt thành công.",
                customer_name="Test Customer",
                plan="yearly",
                paid_at="2026-08-19T14:48:00+07:00",
                expires_at="2027-08-19T14:48:00+07:00",
                mac="F0:68:E3:C4:D1:A1",
            )

    payment_service = RecordingPaymentService()
    license_service = RecordingLicenseService()
    window, _ = _window(
        qtbot,
        settings,
        payment_service=payment_service,
        license_service=license_service,
    )

    window.nav_payment_button.click()

    page = window.payment_page
    assert window.page_stack.currentIndex() == 3
    assert window.nav_payment_button.isChecked()
    assert not window.nav_contact_button.isChecked()
    assert page.payment_card.maximumWidth() == THEME.content_reading_width
    assert page.license_card.findChild(
        QLabel,
        "licenseSectionTitle",
    ).text() == "Nhập mã kích hoạt"
    assert page.license_card.findChild(
        QLabel,
        "licenseSectionHint",
    ).text() == (
        "Nhập mã kích hoạt được cung cấp theo hướng dẫn để xác thực "
        "và kích hoạt ứng dụng."
    )
    assert (
        abs(
            page.payment_card.mapTo(
                page,
                page.payment_card.rect().center(),
            ).x()
            - page.rect().center().x()
        )
        <= THEME.space_1
    )
    assert page.findChild(QLineEdit, "paymentMacAddress") is None
    assert page.findChild(QPushButton, "copyMacButton") is None
    assert [
        page.plan_combo.itemData(index)
        for index in range(page.plan_combo.count())
    ] == [None, "monthly", "quarterly", "semiannual", "yearly", "lifetime"]
    assert [
        page.plan_combo.itemText(index)
        for index in range(1, page.plan_combo.count())
    ] == [
        "1 tháng · 99.000 VNĐ",
        "3 tháng · 249.000 VNĐ",
        "6 tháng · 449.000 VNĐ",
        "1 năm · 799.000 VNĐ",
        "Vĩnh viễn · 1.999.000 VNĐ",
    ]
    assert page.plan_price_label.text() == "Chọn gói để xem giá."

    page.send_button.click()
    assert page.payment_status_label.text() == "Vui lòng nhập họ và tên."

    page.name_input.setText("Nguyễn Văn A")
    page.email_input.setText("email-khong-hop-le")
    page.send_button.click()
    assert page.payment_status_label.text() == "Email không đúng định dạng."

    page.email_input.setText("example@gmail.com")
    page.send_button.click()
    assert page.payment_status_label.text() == "Vui lòng chọn gói thanh toán."

    page.plan_combo.setCurrentIndex(page.plan_combo.findData("monthly"))
    assert page.plan_price_label.text() == "Giá gói: 99.000 VNĐ"
    page.send_button.click()
    assert not page.send_button.isEnabled()
    assert page.send_button.text() == "Đang gửi..."
    qtbot.waitUntil(
        lambda: page.payment_status_label.text().startswith(
            "Yêu cầu thanh toán đã được gửi."
        ),
        timeout=2_000,
    )
    qtbot.waitUntil(page.send_button.isEnabled, timeout=2_000)
    assert len(payment_service.requests) == 1
    assert payment_service.requests[0].to_payload() == {
        "name": "Nguyễn Văn A",
        "email": "example@gmail.com",
        "plan": "monthly",
        "price": 1_990_000,
        "mac": payment_service.requests[0].mac,
    }
    assert len(payment_service.requests[0].mac.split(":")) == 6

    page.activate_button.click()
    assert page.license_status_label.text() == "Vui lòng nhập mã kích hoạt."
    assert license_service.keys == []

    page.license_key_input.setText("TEST-LICENSE-KEY")
    page.activate_button.click()
    assert license_service.keys == ["TEST-LICENSE-KEY"]
    assert page.license_status_label.text() == (
        "✓ Xác thực mã kích hoạt thành công."
    )
    assert page.license_info_widget.isVisible()
    assert page.license_plan_value.text() == "1 năm"
    assert page.license_customer_value.text() == "Test Customer"
    assert page.license_paid_at_value.text() == "19/08/2026"
    assert page.license_expires_at_value.text() == "19/08/2027"
    assert not window.nav_compose_button.license_locked
    assert not window.nav_clone_button.license_locked

    page.license_key_input.clear()
    page.activate_button.click()
    assert not page.license_info_widget.isVisible()
    assert page.license_status_label.text() == "Vui lòng nhập mã kích hoạt."

    window.nav_contact_button.click()
    assert window.page_stack.currentIndex() == 4
    window.nav_payment_button.click()
    assert window.page_stack.currentIndex() == 3
    assert window.nav_payment_button.isChecked()


def test_contact_page_displays_company_details(
    qtbot, settings: Settings
) -> None:  # type: ignore[no-untyped-def]
    window, _ = _window(qtbot, settings)

    window.nav_contact_button.click()

    assert window.page_stack.currentIndex() == 4
    assert window.nav_contact_button.isChecked()
    assert not window.nav_compose_button.isChecked()
    assert not window.nav_clone_button.isChecked()
    assert not window.nav_settings_button.isChecked()
    assert not window.nav_payment_button.isChecked()
    assert window.contact_page.card.maximumWidth() == THEME.content_reading_width
    company_logo = window.contact_page.findChild(QLabel, "contactCompanyIcon")
    assert company_logo is not None
    assert not company_logo.pixmap().isNull()
    assert (
        abs(
            window.contact_page.card.geometry().center().x()
            - window.contact_page.rect().center().x()
        )
        <= THEME.space_1
    )
    assert (
        window.contact_page.company_name_label.text()
        == "CÔNG TY CỔ PHẦN ĐẦU TƯ GIẢI PHÁP HỮU ÍCH"
    )
    assert window.contact_page.address_label.text() == (
        "Lô 17, Khu nhà liền kề Chung cư Simona, đường Hoàng Văn Thụ, "
        "Phường Quy Nhơn Nam, Tỉnh Gia Lai"
    )
    assert settings.application.phone in window.contact_page.phone_label.text()
    assert (
        settings.application.support_email
        in window.contact_page.email_label.text()
    )
    assert settings.application.website in window.contact_page.website_label.text()
    assert (
        settings.application.support_email
        in window.contact_page.support_email_label.text()
    )
    assert not window.contact_page.license_link_label.isVisible()
    assert (
        window.sidebar_copyright_label.text()
        == settings.application.copyright
    )
    assert not window.contact_page.license_link_label.openExternalLinks()
    assert window.contact_page.license_link_label.text() == (
        "Phần mềm này sử dụng Qt/PySide6 và các thành phần "
        "mã nguồn mở khác. "
        "Thông tin giấy phép được cung cấp trong thư mục "
        "_internal/licenses"
    )
    card_layout = window.contact_page.card.layout()
    toggle_item = card_layout.itemAt(
        card_layout.indexOf(window.contact_page.license_toggle_button)
    )
    link_item = card_layout.itemAt(
        card_layout.indexOf(window.contact_page.license_link_label)
    )
    assert toggle_item.alignment() == Qt.AlignmentFlag.AlignRight
    assert link_item.alignment() == Qt.AlignmentFlag(0)
    assert (
        window.contact_page.license_link_label.sizePolicy().horizontalPolicy()
        == QSizePolicy.Policy.Expanding
    )

    window.contact_page.license_toggle_button.click()

    assert window.contact_page.license_toggle_button.isChecked()
    assert window.contact_page.license_link_label.isVisible()

    window.contact_page.set_info(
        "Công ty thử nghiệm",
        "Địa chỉ thử nghiệm",
        "0123 456 789",
        "support@example.com",
        "example.com",
    )

    assert 'href="tel:0123%20456%20789"' in window.contact_page.phone_label.text()
    assert 'href="mailto:support@example.com"' in window.contact_page.email_label.text()
    assert 'href="https://example.com"' in window.contact_page.website_label.text()
    assert window.contact_page.phone_label.openExternalLinks()
    assert window.contact_page.email_label.openExternalLinks()
    assert window.contact_page.website_label.openExternalLinks()
    assert (
        window.sidebar_copyright_label.text()
        == settings.application.copyright
    )


def test_style_selection_is_independent_from_voice(
    qtbot, settings: Settings
) -> None:  # type: ignore[no-untyped-def]
    window, _ = _window(qtbot, settings)
    original_voice = window.voice_selector.current_voice_id()

    window.voice_style.style_combo.setCurrentIndex(1)

    assert window.voice_style.current_style_id() == "tin_tuc"
    assert window.voice_selector.current_voice_id() == original_voice


def test_reset_button_restores_voice_style_defaults(
    qtbot, settings: Settings
) -> None:  # type: ignore[no-untyped-def]
    window, _ = _window(qtbot, settings)
    voice_style = window.voice_style
    default_speed = round(settings.audio.default_speed * 10)
    default_pitch = round(settings.audio.default_pitch_semitones)
    default_volume = round(settings.audio.default_volume_db)

    assert not voice_style.reset_button.isEnabled()
    assert voice_style.reset_button.objectName() == "resetVoiceStyleButton"
    assert (
        voice_style.reset_button.accessibleName()
        == "Đặt lại phong cách giọng nói về mặc định"
    )

    voice_style.style_combo.setCurrentIndex(
        voice_style.style_combo.findData("tin_tuc")
    )
    voice_style.speed_slider.setValue(default_speed + 1)
    voice_style.pitch_slider.setValue(default_pitch + 1)
    voice_style.volume_slider.setValue(default_volume - 1)

    assert voice_style.reset_button.isEnabled()

    voice_style.reset_button.click()

    assert voice_style.current_style_id() == "tu_nhien"
    assert voice_style.speed_slider.value() == default_speed
    assert voice_style.pitch_slider.value() == default_pitch
    assert voice_style.volume_slider.value() == default_volume
    assert not voice_style.reset_button.isEnabled()


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


def test_cancelled_synthesis_restores_normal_ui(qtbot, settings: Settings) -> None:  # type: ignore[no-untyped-def]
    window, view_model = _window(qtbot, settings)
    window.text_input.editor.setPlainText("Dừng tác vụ tổng hợp đang chạy.")

    window.synthesize_button.click()
    qtbot.waitUntil(lambda: view_model.state == "synthesizing", timeout=1_000)
    window.cancel_button.click()

    qtbot.waitUntil(lambda: view_model.state == "cancelled", timeout=3_000)
    assert not window.cancel_button.isVisible()
    assert window.synthesize_button.isEnabled()
    assert window.text_input.open_file_button.isEnabled()
    assert not window.waveform.has_audio


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
