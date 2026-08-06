"""Shared test configuration and fixtures."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from vntts.config.settings import Settings, load_settings  # noqa: E402


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Return settings whose writable data root is isolated per test."""

    monkeypatch.setenv("VNTTS_APP_DATA_DIR", str(tmp_path / "app-data"))
    return load_settings()

