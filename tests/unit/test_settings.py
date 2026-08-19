"""Tests for YAML settings, platform paths and logging."""

from pathlib import Path

import pytest
from loguru import logger

import vntts.config.settings as settings_module
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


def test_payment_endpoint_can_be_configured_from_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VNTTS_APP_DATA_DIR", str(tmp_path / "app-data"))
    monkeypatch.setenv(
        "VNTTS_PAYMENT_API_ENDPOINT",
        "https://example.com/api/payment/request",
    )

    result = load_settings(create_directories=False)

    assert result.payment.api_endpoint == (
        "https://example.com/api/payment/request"
    )
    assert result.payment.request_timeout_seconds == 10
    assert result.payment.plan_prices_vnd == {
        "monthly": 99_000,
        "quarterly": 249_000,
        "semiannual": 449_000,
        "yearly": 799_000,
        "lifetime": 1_999_000,
    }


def test_production_defaults_to_bundled_vieneu_v3(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VNTTS_APP_DATA_DIR", str(tmp_path / "app-data"))
    monkeypatch.setenv("VNTTS_ENVIRONMENT", "production")

    result = load_settings(create_directories=False)

    assert result.tts.default_engine == "vieneu-v3"


def test_application_contact_fields_are_optional_and_normalized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "contact-settings.yaml"
    config_path.write_text(
        """
application:
  name: GPHI-TTS
  environment: development
  manufacturer: "  Công ty thử nghiệm  "
  address: "  Địa chỉ thử nghiệm  "
  phone: ""
  website: "  example.com  "
  support_email: "  support@example.com  "
  copyright: ""
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("VNTTS_APP_DATA_DIR", str(tmp_path / "app-data"))

    result = load_settings(config_path, create_directories=False)

    assert result.application.manufacturer == "Công ty thử nghiệm"
    assert result.application.address == "Địa chỉ thử nghiệm"
    assert result.application.phone == ""
    assert result.application.website == "example.com"
    assert result.application.support_email == "support@example.com"
    assert result.application.copyright == ""


def test_frozen_build_defaults_to_production_and_meipass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frozen_root = tmp_path / "frozen"
    monkeypatch.setattr(settings_module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(settings_module.sys, "_MEIPASS", str(frozen_root), raising=False)
    monkeypatch.delenv("VNTTS_ENVIRONMENT", raising=False)
    monkeypatch.setenv("VNTTS_APP_DATA_DIR", str(tmp_path / "app-data"))

    result = load_settings(create_directories=False)

    assert result.application.environment == "production"
    assert result.paths.bundled_models_dir == (frozen_root / "resources/models").resolve()


def test_logging_writes_rotating_file_without_payload(settings: Settings) -> None:
    configure_logging(settings)
    sensitive_text = "VĂN BẢN NHẠY CẢM KHÔNG ĐƯỢC GHI"

    logger.info("Tác vụ tổng hợp bắt đầu", text_length=len(sensitive_text))
    logger.complete()
    content = (settings.paths.logs_dir / "vntts.log").read_text(encoding="utf-8")

    assert "Tác vụ tổng hợp bắt đầu" in content
    assert sensitive_text not in content
