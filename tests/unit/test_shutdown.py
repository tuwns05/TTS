"""Exercise real process exit while a model loader refuses cancellation."""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


@pytest.mark.parametrize("close_target", ["popup", "window"])
def test_exit_during_blocked_model_load(tmp_path, close_target):
    script = textwrap.dedent("""
        import sys
        from threading import Event
        from unittest.mock import patch
        from PySide6.QtCore import QTimer
        import vntts.main as entry
        from vntts.db.models import HardwareInfo
        from vntts.services.license_service import LicenseActivationResult

        loading = Event()
        def blocked_load(self, device):
            loading.set()
            Event().wait(60)

        build = entry.build_application
        def build_test_application():
            app, window = build()
            def close_when_loading():
                if not loading.is_set():
                    QTimer.singleShot(10, close_when_loading)
                    return
                popup = window._model_loading_popup
                assert popup is not None
                print('closing during model load', flush=True)
                target = popup if sys.argv[1] == 'popup' else window
                target.close()
            QTimer.singleShot(10, close_when_loading)
            return app, window

        hardware = HardwareInfo(
            cpu_name='Test', physical_cores=4, logical_cores=8, ram_gb=8,
            gpu_name=None, vram_gb=None, cuda_available=False,
            operating_system='Test', architecture='x64',
        )
        with (
            patch.object(entry, 'build_application', build_test_application),
            patch.object(entry.HardwareDetector, 'detect', return_value=hardware),
            patch.object(entry.LicenseService, 'validate_saved', return_value=
                LicenseActivationResult(activated=True, message='Test')),
            patch.object(entry.VieNeuV3Engine, 'is_available', return_value=True),
            patch.object(entry.VieNeuV3Engine, 'load', blocked_load),
        ):
            raise SystemExit(entry.main())
    """)
    env = {
        **os.environ,
        "QT_QPA_PLATFORM": "offscreen",
        "VNTTS_APP_DATA_DIR": str(tmp_path / "app-data"),
        "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src"),
    }
    result = subprocess.run(
        [sys.executable, "-c", script, close_target],
        env=env, capture_output=True, text=True, timeout=20, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "closing during model load" in result.stdout
