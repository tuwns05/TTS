"""Tests for local machine identifiers."""

import pytest

import vntts.utils.machine_info as machine_info_module
from vntts.utils.machine_info import get_mac_address


def test_formats_mac_address_with_uppercase_pairs() -> None:
    assert get_mac_address(lambda: 0xA1B2C3D4E5F6) == "A1:B2:C3:D4:E5:F6"


def test_rejects_out_of_range_machine_node() -> None:
    with pytest.raises(ValueError, match="MAC hợp lệ"):
        get_mac_address(lambda: 1 << 48)


def test_prefers_physical_ethernet_mac(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        machine_info_module,
        "_get_windows_physical_ethernet_mac",
        lambda: "E8:9C:25:4C:E3:60",
    )
    monkeypatch.setattr(
        machine_info_module.uuid,
        "getnode",
        lambda: 0xA1B2C3D4E5F6,
    )

    assert get_mac_address() == "E8:9C:25:4C:E3:60"


def test_falls_back_to_uuid_when_ethernet_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        machine_info_module,
        "_get_windows_physical_ethernet_mac",
        lambda: None,
    )
    monkeypatch.setattr(
        machine_info_module.uuid,
        "getnode",
        lambda: 0xA1B2C3D4E5F6,
    )

    assert get_mac_address() == "A1:B2:C3:D4:E5:F6"
