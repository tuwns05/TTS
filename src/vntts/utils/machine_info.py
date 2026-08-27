"""Stable, presentation-ready identifiers for the local machine."""

from __future__ import annotations

import re
import subprocess
import sys
import uuid
from collections.abc import Callable
from functools import lru_cache


_MAC_PATTERN = re.compile(r"^[0-9A-F]{12}$")


def _normalize_mac_address(value: str) -> str:
    """Normalize a MAC address to conventional uppercase colon notation."""

    hexadecimal = value.strip().upper().replace(":", "").replace("-", "")
    if not _MAC_PATTERN.fullmatch(hexadecimal):
        raise ValueError("Không thể xác định địa chỉ MAC hợp lệ.")
    return ":".join(
        hexadecimal[index : index + 2] for index in range(0, 12, 2)
    )


@lru_cache(maxsize=1)
def _get_windows_physical_ethernet_mac() -> str | None:
    """Return a physical Ethernet adapter MAC on Windows, when available."""

    if sys.platform != "win32":
        return None

    command = (
        "$adapter = Get-NetAdapter -Physical -ErrorAction Stop | "
        "Where-Object { $_.InterfaceType -eq 6 -and $_.MacAddress } | "
        "Sort-Object InterfaceIndex | Select-Object -First 1; "
        "if ($null -ne $adapter) { "
        "if ($adapter.PermanentAddress) { $adapter.PermanentAddress } "
        "else { $adapter.MacAddress } }"
    )
    try:
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                command,
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if not completed.stdout.strip():
        return None
    try:
        return _normalize_mac_address(completed.stdout)
    except ValueError:
        return None


def get_mac_address(
    node_provider: Callable[[], int] | None = None,
) -> str:
    """Return the physical Ethernet MAC, falling back to ``uuid.getnode``."""

    if node_provider is None:
        ethernet_mac = _get_windows_physical_ethernet_mac()
        if ethernet_mac is not None:
            return ethernet_mac
        node_provider = uuid.getnode

    node = node_provider()
    if not isinstance(node, int) or not 0 <= node < (1 << 48):
        raise ValueError("Không thể xác định địa chỉ MAC hợp lệ.")
    return _normalize_mac_address(f"{node:012X}")
