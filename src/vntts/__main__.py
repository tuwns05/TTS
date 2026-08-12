"""Run the application with ``python -m vntts`` or as a frozen executable."""

from __future__ import annotations

import atexit
import ctypes
import multiprocessing
import sys

_ERROR_ALREADY_EXISTS = 183
_instance_mutex: int | None = None


def _acquire_frozen_instance_mutex() -> bool:
    """Allow only one frozen GUI process before importing Qt and PyTorch."""

    global _instance_mutex
    if not sys.platform.startswith("win") or not getattr(sys, "frozen", False):
        return True

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_mutex = kernel32.CreateMutexW
    create_mutex.argtypes = (ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p)
    create_mutex.restype = ctypes.c_void_p
    handle = create_mutex(None, False, "Local\\GPHI-TTS-0.1.0-SingleInstance")
    if not handle:
        return False
    if ctypes.get_last_error() == _ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return False

    _instance_mutex = int(handle)

    def release_mutex() -> None:
        global _instance_mutex
        if _instance_mutex is not None:
            kernel32.CloseHandle(_instance_mutex)
            _instance_mutex = None

    atexit.register(release_mutex)
    return True


multiprocessing.freeze_support()
if not _acquire_frozen_instance_mutex():
    raise SystemExit(0)

def _run_application() -> int:
    """Import the heavy application graph only after frozen-process guards."""

    # This local static import remains visible to PyInstaller while still
    # deferring Qt and NumPy until the instance guard has passed.
    from vntts.main import main

    return main()


raise SystemExit(_run_application())
