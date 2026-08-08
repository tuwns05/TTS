"""Application composition root and executable entry point."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from loguru import logger
from PySide6.QtWidgets import QApplication

from vntts.config.settings import Settings, load_settings
from vntts.config.theme import build_stylesheet
from vntts.engines.factory import EngineFactory, EngineLifecycleManager, EngineRegistry
from vntts.engines.kokoro_engine import KokoroVIEngine
from vntts.engines.vieneu_engine import VieNeuV2Engine, VieNeuV3Engine
from vntts.services.hardware import EngineRecommendationService, HardwareDetector
from vntts.services.synthesis import SynthesizeSpeech
from vntts.ui.compose_view import MainViewModel
from vntts.ui.main_window import MainWindow
from vntts.ui.fonts import load_app_fonts
from vntts.utils.logger import configure_logging, shutdown_logging


def build_application(argv: Sequence[str] | None = None) -> tuple[QApplication, MainWindow]:
    """Compose engine adapters lazily without loading models on the UI thread."""

    settings: Settings = load_settings()
    configure_logging(settings)
    application = QApplication.instance() or QApplication(list(argv or sys.argv))
    load_app_fonts()
    application.setApplicationName(settings.application.name)
    application.setStyleSheet(build_stylesheet())

    registry = EngineRegistry()
    bundled_v3 = settings.paths.bundled_models_dir / "vieneu-v3"
    optional_v2 = settings.paths.models_dir / "vieneu-v2"
    optional_kokoro = settings.paths.models_dir / "kokoro-vi"

    is_production = settings.application.environment.strip().lower() == "production"
    local_v3 = bundled_v3 if bundled_v3.is_dir() else None
    local_v3_tokenizer = bundled_v3 / "moss-tokenizer"
    v3_provider = lambda: VieNeuV3Engine(  # noqa: E731
        local_v3,
        tokenizer_path=(local_v3_tokenizer if local_v3_tokenizer.is_dir() else None),
        allow_download=not is_production,
    )
    v2_provider = lambda: VieNeuV2Engine(  # noqa: E731
        optional_v2 / "backbone",
        optional_v2 / "codec",
    )
    kokoro_provider = lambda: KokoroVIEngine(  # noqa: E731
        optional_kokoro / "kokoro_vi.pth",
        optional_kokoro / "config.json",
        optional_kokoro / "voicepacks",
    )

    registry.register(
        VieNeuV3Engine.INFO.engine_id,
        v3_provider,
        VieNeuV3Engine.INFO,
        VieNeuV3Engine.CAPABILITIES,
    )
    for provider, info, capabilities in (
        (v2_provider, VieNeuV2Engine.INFO, VieNeuV2Engine.CAPABILITIES),
        (kokoro_provider, KokoroVIEngine.INFO, KokoroVIEngine.CAPABILITIES),
    ):
        if provider().is_available():
            registry.register(info.engine_id, provider, info, capabilities)

    factory = EngineFactory(registry)
    lifecycle = EngineLifecycleManager(factory)
    use_case = SynthesizeSpeech(
        factory,
        registry,
        max_text_length=settings.tts.max_text_length,
        lifecycle=lifecycle,
    )
    hardware = HardwareDetector().detect()
    recommendation = EngineRecommendationService(
        settings.hardware_recommendation
    ).recommend(hardware)
    view_model = MainViewModel(registry, use_case, settings, recommendation)
    window = MainWindow(view_model, settings)

    logger.info(
        "Ứng dụng khởi động",
        environment=settings.application.environment,
        registered_engines=registry.list_engine_ids(),
    )
    application.aboutToQuit.connect(shutdown_logging)
    return application, window


def main() -> int:
    """Start the Qt event loop."""

    application, window = build_application()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
