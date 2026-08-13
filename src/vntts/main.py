"""Application composition root and executable entry point."""

from __future__ import annotations

import sys
import wave
from collections.abc import Sequence
from multiprocessing import freeze_support
from pathlib import Path

import numpy as np
from loguru import logger
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from vntts.config.settings import Settings, load_settings
from vntts.config.theme import THEME, build_stylesheet, get_system_font
from vntts.db.models import EngineSynthesisOptions
from vntts.engines.factory import EngineFactory, EngineLifecycleManager, EngineRegistry
from vntts.engines.vieneu_engine import VieNeuV3Engine
from vntts.services.hardware import HardwareDetector
from vntts.services.playback import PlaybackService
from vntts.services.synthesis import SynthesizeSpeech
from vntts.services.voice_enrollment import VoiceEnrollmentService
from vntts.services.voice_profiles import VoiceProfileStore
from vntts.ui.compose_view import MainViewModel
from vntts.ui.fonts import load_app_fonts
from vntts.ui.main_window import MainWindow
from vntts.utils.logger import configure_logging, shutdown_logging


def build_application(argv: Sequence[str] | None = None) -> tuple[QApplication, MainWindow]:
    """Compose engine adapters lazily without loading models on the UI thread."""

    settings: Settings = load_settings()
    configure_logging(settings)
    application = QApplication.instance() or QApplication(list(argv or sys.argv))
    application.setStyle("Fusion")
    load_app_fonts()
    application.setApplicationName(settings.application.name)
    application.setFont(get_system_font())
    application.setStyleSheet(build_stylesheet(THEME))

    registry = EngineRegistry()
    bundled_v3 = settings.paths.bundled_models_dir / "vieneu-v3"
    is_production = settings.application.environment.strip().lower() == "production"
    is_model_bundle = (bundled_v3 / "manifest.json").is_file()
    local_v3 = bundled_v3 if bundled_v3.is_dir() and not is_model_bundle else None
    local_v3_tokenizer = bundled_v3 / "moss-tokenizer"
    v3_provider = lambda: VieNeuV3Engine(
        local_v3,
        tokenizer_path=(local_v3_tokenizer if local_v3_tokenizer.is_dir() else None),
        bundle_path=(bundled_v3 if is_model_bundle else None),
        bundle_cache_dir=settings.paths.cache_dir,
        allow_download=not is_production,
        backend="auto",
    )

    registry.register(
        VieNeuV3Engine.INFO.engine_id,
        v3_provider,
        VieNeuV3Engine.INFO,
        VieNeuV3Engine.CAPABILITIES,
    )
    factory = EngineFactory(registry)
    lifecycle = EngineLifecycleManager(factory)
    use_case = SynthesizeSpeech(
        factory,
        registry,
        lifecycle=lifecycle,
    )
    voice_profile_store = VoiceProfileStore(settings.paths.data_dir)
    voice_enrollment = VoiceEnrollmentService(use_case, voice_profile_store)
    view_model = MainViewModel(
        registry,
        use_case,
        settings,
        None,
        hardware_detector=HardwareDetector().detect,
        voice_enrollment_service=voice_enrollment,
    )
    window = MainWindow(
        view_model,
        settings,
        voice_profile_store=voice_profile_store,
    )

    logger.info(
        "Ứng dụng khởi động",
        environment=settings.application.environment,
        registered_engines=registry.list_engine_ids(),
    )
    application.aboutToQuit.connect(shutdown_logging)
    return application, window


def main() -> int:
    """Start the Qt event loop."""

    freeze_support()

    if len(sys.argv) in {3, 4} and sys.argv[1] == "--production-smoke":
        device = sys.argv[3] if len(sys.argv) == 4 else "cpu"
        return _run_production_smoke(Path(sys.argv[2]), device)

    application, window = build_application()
    window.show()
    QTimer.singleShot(0, window.start_initialization)
    return application.exec()


def _run_production_smoke(output_path: Path, device: str = "cpu") -> int:
    """Verify that the frozen artifact can load and synthesize real audio."""

    settings = load_settings()
    configure_logging(settings)
    engine = VieNeuV3Engine(
        bundle_path=settings.paths.bundled_models_dir / "vieneu-v3",
        bundle_cache_dir=settings.paths.cache_dir,
        allow_download=False,
        backend="auto",
    )
    try:
        engine.load(device)
        voice = engine.list_voices()[0]
        result = engine.synthesize(
            "Xin chào, đây là bản kiểm tra đóng gói.",
            EngineSynthesisOptions(voice_id=voice.voice_id),
        )
        pcm = np.rint(np.clip(result.audio, -1.0, 1.0) * 32_767).astype("<i2")
        if pcm.size == 0:
            raise RuntimeError("Smoke synthesis returned empty audio.")
        destination = output_path.expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(destination), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(result.sample_rate)
            output.writeframes(pcm.tobytes())
        destination.with_suffix(".mp3").write_bytes(
            PlaybackService._encode_mp3(result)
        )
        logger.info(
            "Production smoke synthesis succeeded",
            samples=int(pcm.size),
            sample_rate=result.sample_rate,
            device=engine.runtime_info.device if engine.runtime_info else None,
            backend=engine.runtime_info.backend if engine.runtime_info else None,
        )
        return 0
    except Exception:  # noqa: BLE001 - smoke command converts all failures to exit code 1
        logger.exception("Production smoke synthesis failed")
        return 1
    finally:
        if engine.is_loaded():
            engine.unload()
        shutdown_logging()


if __name__ == "__main__":
    raise SystemExit(main())
