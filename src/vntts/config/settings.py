"""Load, validate and normalize application settings."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import yaml

from vntts.db.models import HardwareRecommendationSettings, TierSettings
from vntts.utils.exceptions import ConfigurationError

_SAFE_DEFAULTS: dict[str, object] = {
    "application": {
        "name": "Vietnamese TTS Desktop",
        "environment": "development",
        "manufacturer": "",
        "address": "",
        "phone": "",
        "website": "",
        "support_email": "",
        "copyright": "",
    },
    "paths": {
        "bundled_models_dir": "resources/models",
        "models_dir": "models",
        "data_dir": "data",
        "cache_dir": "data/cache",
        "logs_dir": "data/logs",
    },
    "tts": {
        "default_engine": "vieneu-v3",
        "production_default_engine": "vieneu-v3",
    },
    "audio": {
        "default_speed": 1.0,
        "default_pitch_semitones": 0.0,
        "default_volume_db": 0.0,
        "default_sample_rate": 24_000,
    },
    "hardware_recommendation": {
        "high_tier": {"min_ram_gb": 16, "min_physical_cores": 6, "min_vram_gb": 6},
        "medium_tier": {"min_ram_gb": 8, "min_physical_cores": 4},
    },
    "logging": {"level": "INFO", "retention_days": 7},
}


@dataclass(frozen=True)
class ApplicationSettings:
    """Application identity and runtime environment."""

    name: str
    environment: str
    manufacturer: str = ""
    website: str = ""
    support_email: str = ""
    copyright: str = ""
    address: str = ""
    phone: str = ""


@dataclass(frozen=True)
class PathSettings:
    """Normalized local storage paths."""

    bundled_models_dir: Path
    models_dir: Path
    data_dir: Path
    cache_dir: Path
    logs_dir: Path


@dataclass(frozen=True)
class TTSSettings:
    """Cross-engine synthesis settings."""

    default_engine: str


@dataclass(frozen=True)
class AudioSettings:
    """Default audio controls shown by the UI."""

    default_speed: float
    default_pitch_semitones: float
    default_volume_db: float
    default_sample_rate: int


@dataclass(frozen=True)
class LoggingSettings:
    """Logging verbosity and retention policy."""

    level: str
    retention_days: int


@dataclass(frozen=True)
class Settings:
    """Validated application configuration."""

    application: ApplicationSettings
    paths: PathSettings
    tts: TTSSettings
    audio: AudioSettings
    hardware_recommendation: HardwareRecommendationSettings
    logging: LoggingSettings


def _application_data_root() -> Path:
    override = os.getenv("VNTTS_APP_DATA_DIR")
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        base = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "VietnameseTTSDesktop"


def _installation_root() -> Path:
    """Return the read-only application root in source and frozen builds."""

    if getattr(sys, "frozen", False):
        frozen_root = getattr(sys, "_MEIPASS", None)
        return (
            Path(frozen_root).resolve()
            if frozen_root
            else Path(sys.executable).resolve().parent
        )
    return Path(__file__).resolve().parents[3]


def _merge(base: dict[str, object], override: Mapping[str, object]) -> dict[str, object]:
    merged = deepcopy(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, Mapping):
            merged[key] = _merge(current, value)
        else:
            merged[key] = value
    return merged


def _section(config: Mapping[str, object], name: str) -> Mapping[str, object]:
    value = config.get(name)
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"Mục cấu hình '{name}' phải là một mapping.")
    return value


def _number(value: object, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"'{label}' phải là số.")
    numeric = float(value)
    if positive and numeric <= 0:
        raise ConfigurationError(f"'{label}' phải lớn hơn 0.")
    return numeric


def _optional_text(value: object, label: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ConfigurationError(f"'{label}' phải là chuỗi.")
    return value.strip()


def _resolve_path(value: object, root: Path, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"'{label}' phải là đường dẫn hợp lệ.")
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def load_settings(config_path: Path | None = None, *, create_directories: bool = True) -> Settings:
    """Load YAML settings, apply environment overrides and create local directories."""

    path = config_path or Path(__file__).with_name("default.yaml")
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigurationError(f"Không thể đọc cấu hình: {path}") from exc
    if not isinstance(loaded, Mapping):
        raise ConfigurationError("Nội dung cấu hình gốc phải là một mapping.")

    config = _merge(_SAFE_DEFAULTS, loaded)
    app = _section(config, "application")
    paths = _section(config, "paths")
    tts = _section(config, "tts")
    audio = _section(config, "audio")
    hardware = _section(config, "hardware_recommendation")
    high = _section(hardware, "high_tier")
    medium = _section(hardware, "medium_tier")
    logging_config = _section(config, "logging")

    app_root = _application_data_root()
    path_overrides = {
        "models_dir": os.getenv("VNTTS_MODELS_DIR"),
        "data_dir": os.getenv("VNTTS_DATA_DIR"),
        "cache_dir": os.getenv("VNTTS_CACHE_DIR"),
        "logs_dir": os.getenv("VNTTS_LOGS_DIR"),
    }
    normalized_paths: dict[str, Path] = {}
    for key, override in path_overrides.items():
        normalized_paths[key] = _resolve_path(
            override or paths.get(key), app_root, f"paths.{key}"
        )
    normalized_paths["bundled_models_dir"] = _resolve_path(
        os.getenv("VNTTS_BUNDLED_MODELS_DIR") or paths.get("bundled_models_dir"),
        _installation_root(),
        "paths.bundled_models_dir",
    )

    application_name = app.get("name")
    environment = os.getenv("VNTTS_ENVIRONMENT")
    if environment is None:
        environment = "production" if getattr(sys, "frozen", False) else app.get("environment")
    default_engine = os.getenv("VNTTS_DEFAULT_ENGINE")
    if default_engine is None:
        default_engine = (
            tts.get("production_default_engine")
            if str(environment).strip().lower() == "production"
            else tts.get("default_engine")
        )
    if not isinstance(application_name, str) or not application_name.strip():
        raise ConfigurationError("Tên ứng dụng không được để trống.")
    if not isinstance(environment, str) or not environment.strip():
        raise ConfigurationError("Môi trường ứng dụng không được để trống.")
    if not isinstance(default_engine, str) or not default_engine.strip():
        raise ConfigurationError("Engine mặc định không được để trống.")

    sample_rate = int(_number(audio.get("default_sample_rate"), "audio.default_sample_rate", positive=True))
    retention_days = int(_number(logging_config.get("retention_days"), "logging.retention_days", positive=True))
    level_value = os.getenv("VNTTS_LOG_LEVEL") or logging_config.get("level")
    if not isinstance(level_value, str) or not level_value.strip():
        raise ConfigurationError("Mức logging không hợp lệ.")

    settings = Settings(
        application=ApplicationSettings(
            name=application_name.strip(),
            environment=environment.strip(),
            manufacturer=_optional_text(
                app.get("manufacturer"), "application.manufacturer"
            ),
            website=_optional_text(app.get("website"), "application.website"),
            support_email=_optional_text(
                app.get("support_email"), "application.support_email"
            ),
            copyright=_optional_text(
                app.get("copyright"), "application.copyright"
            ),
            address=_optional_text(app.get("address"), "application.address"),
            phone=_optional_text(app.get("phone"), "application.phone"),
        ),
        paths=PathSettings(**normalized_paths),
        tts=TTSSettings(default_engine),
        audio=AudioSettings(
            _number(audio.get("default_speed"), "audio.default_speed"),
            _number(audio.get("default_pitch_semitones"), "audio.default_pitch_semitones"),
            _number(audio.get("default_volume_db"), "audio.default_volume_db"),
            sample_rate,
        ),
        hardware_recommendation=HardwareRecommendationSettings(
            high_tier=TierSettings(
                _number(high.get("min_ram_gb"), "high_tier.min_ram_gb", positive=True),
                int(_number(high.get("min_physical_cores"), "high_tier.min_physical_cores", positive=True)),
                _number(high.get("min_vram_gb"), "high_tier.min_vram_gb", positive=True),
            ),
            medium_tier=TierSettings(
                _number(medium.get("min_ram_gb"), "medium_tier.min_ram_gb", positive=True),
                int(_number(medium.get("min_physical_cores"), "medium_tier.min_physical_cores", positive=True)),
            ),
        ),
        logging=LoggingSettings(level_value.upper(), retention_days),
    )

    if create_directories:
        try:
            for directory in {
                settings.paths.models_dir,
                settings.paths.data_dir,
                settings.paths.cache_dir,
                settings.paths.logs_dir,
            }:
                directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ConfigurationError("Không thể tạo thư mục dữ liệu ứng dụng.") from exc
    return settings
