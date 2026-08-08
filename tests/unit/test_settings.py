"""Tests for YAML settings, platform paths and logging."""

from pathlib import Path

import pytest
from loguru import logger

from vntts.config.settings import Settings, load_settings
from vntts.utils.logger import configure_logging


def test_settings_use_isolated_application_data_root(settings: Settings, tmp_path: Path) -> None:
    expected_root = (tmp_path / "app-data").resolve()

    assert settings.paths.data_dir == expected_root / "data"
    assert settings.paths.models_dir == expected_root / "models"
    assert settings.paths.cache_dir.is_dir()
    assert settings.paths.logs_dir.is_dir()
    assert settings.paths.bundled_models_dir.name == "models"


def test_environment_path_override_is_respected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    custom_cache = tmp_path / "custom-cache"
    monkeypatch.setenv("VNTTS_APP_DATA_DIR", str(tmp_path / "app-data"))
    monkeypatch.setenv("VNTTS_CACHE_DIR", str(custom_cache))

    result = load_settings()

    assert result.paths.cache_dir == custom_cache.resolve()
    assert custom_cache.is_dir()


def test_production_defaults_to_bundled_vieneu_v3(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VNTTS_APP_DATA_DIR", str(tmp_path / "app-data"))
    monkeypatch.setenv("VNTTS_ENVIRONMENT", "production")

    result = load_settings(create_directories=False)

    assert result.tts.default_engine == "vieneu-v3"


def test_logging_writes_rotating_file_without_payload(settings: Settings) -> None:
    configure_logging(settings)
    sensitive_text = "VĂN BẢN NHẠY CẢM KHÔNG ĐƯỢC GHI"

    logger.info("Tác vụ tổng hợp bắt đầu", text_length=len(sensitive_text))
    logger.complete()
    content = (settings.paths.logs_dir / "vntts.log").read_text(encoding="utf-8")

    assert "Tác vụ tổng hợp bắt đầu" in content
    assert sensitive_text not in content
