"""Application composition root and executable entry point."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from loguru import logger
from PySide6.QtWidgets import QApplication

from vntts.application.services.engine_factory import EngineFactory
from vntts.application.services.engine_recommendation_service import (
    EngineRecommendationService,
)
from vntts.application.services.engine_registry import EngineRegistry
from vntts.application.use_cases.synthesize_speech import SynthesizeSpeech
from vntts.config.settings import Settings, load_settings
from vntts.infrastructure.engines.fake_engine import FakeTTSEngine
from vntts.infrastructure.hardware.hardware_detector import HardwareDetector
from vntts.presentation.main_window import MainWindow
from vntts.presentation.viewmodels.main_viewmodel import MainViewModel
from vntts.utils.logger import configure_logging, shutdown_logging


def build_application(argv: Sequence[str] | None = None) -> tuple[QApplication, MainWindow]:
    """Compose the Phase 1 application without loading a real TTS model."""

    settings: Settings = load_settings()
    configure_logging(settings)
    application = QApplication.instance() or QApplication(list(argv or sys.argv))
    application.setApplicationName(settings.application.name)

    registry = EngineRegistry()
    registry.register(
        FakeTTSEngine.INFO.engine_id,
        lambda: FakeTTSEngine(sample_rate=settings.audio.default_sample_rate),
        FakeTTSEngine.INFO,
    )
    factory = EngineFactory(registry)
    use_case = SynthesizeSpeech(
        factory,
        registry,
        max_text_length=settings.tts.max_text_length,
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

