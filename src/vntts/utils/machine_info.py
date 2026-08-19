"""Stable, presentation-ready identifiers for the local machine."""

from __future__ import annotations

import uuid
from collections.abc import Callable


def get_mac_address(node_provider: Callable[[], int] = uuid.getnode) -> str:
    """Return the machine MAC address using conventional uppercase notation."""

    node = node_provider()
    if not isinstance(node, int) or not 0 <= node < (1 << 48):
        raise ValueError("Không thể xác định địa chỉ MAC hợp lệ.")
    hexadecimal = f"{node:012X}"
    return ":".join(
        hexadecimal[index : index + 2] for index in range(0, 12, 2)
    )
