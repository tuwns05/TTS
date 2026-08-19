"""Tests for offline Ed25519 license verification."""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from vntts.services.license_service import LicenseService
from vntts.utils.exceptions import ValidationError

SAMPLE_LICENSE_KEY = (
    "eyJjdXN0b21lcl9uYW1lIjoiVGVzdCBDdXN0b21lciIsImV4cGlyZXNfYXQiOiIy"
    "MDI3LTA4LTE5VDE0OjQ4OjAwKzA3OjAwIiwibWFjIjoiRjA6Njg6RTM6QzQ6RDE6"
    "QTEiLCJwYWlkX2F0IjoiMjAyNi0wOC0xOVQxNDo0ODowMCswNzowMCIsInBsYW4i"
    "OiJ5ZWFybHkiLCJ2IjoxfQ.88iiJ8rDeLECbwnXEfyZcv5yYQTmOeh35ySbiBZSHAA"
    "3I6qZZyG8mlUP9xe_iTbOhMx4Lm4X2sOPOcspFbFJCg"
)
_TEST_PRIVATE_KEY = "4BI0ollUUzAioL_OdBEiq6at8zDb58ZbEhD4UtkgMgk"
_VALID_NOW = datetime(2026, 8, 20, tzinfo=UTC)


def _service(mac: str = "F0:68:E3:C4:D1:A1") -> LicenseService:
    return LicenseService(
        mac_provider=lambda: mac,
        now_provider=lambda: _VALID_NOW,
    )


def _base64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _signed_key(payload: dict[str, object]) -> str:
    payload_bytes = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    private_key = Ed25519PrivateKey.from_private_bytes(
        _base64url_decode(_TEST_PRIVATE_KEY)
    )
    signature = private_key.sign(payload_bytes)
    return f"{_base64url_encode(payload_bytes)}.{_base64url_encode(signature)}"


def test_accepts_valid_sample_key_for_matching_mac() -> None:
    result = _service("  f0:68:e3:c4:d1:a1  ").activate(SAMPLE_LICENSE_KEY)

    assert result.activated
    assert result.message == "Xác thực mã kích hoạt thành công."
    assert result.customer_name == "Test Customer"
    assert result.plan == "yearly"
    assert result.paid_at == "2026-08-19T14:48:00+07:00"
    assert result.expires_at == "2027-08-19T14:48:00+07:00"
    assert result.mac == "F0:68:E3:C4:D1:A1"


def test_rejects_valid_key_for_another_machine() -> None:
    with pytest.raises(ValidationError, match="không thuộc thiết bị này"):
        _service("00:11:22:33:44:55").activate(SAMPLE_LICENSE_KEY)


def test_rejects_tampered_payload_before_parsing_json() -> None:
    payload, signature = SAMPLE_LICENSE_KEY.split(".")
    replacement = "A" if payload[0] != "A" else "B"
    tampered = f"{replacement}{payload[1:]}.{signature}"

    with pytest.raises(ValidationError, match="đã bị chỉnh sửa"):
        _service().activate(tampered)


def test_rejects_tampered_signature() -> None:
    payload, signature = SAMPLE_LICENSE_KEY.split(".")
    replacement = "A" if signature[-1] != "A" else "B"
    tampered = f"{payload}.{signature[:-1]}{replacement}"

    with pytest.raises(ValidationError, match="đã bị chỉnh sửa"):
        _service().activate(tampered)


def test_rejects_key_without_separator() -> None:
    with pytest.raises(ValidationError, match="không đúng định dạng"):
        _service().activate("not-a-license-key")


def test_rejects_expired_signed_key() -> None:
    expired_key = _signed_key(
        {
            "v": 1,
            "customer_name": "Expired Customer",
            "mac": "F0:68:E3:C4:D1:A1",
            "plan": "monthly",
            "paid_at": "2025-01-01T00:00:00+07:00",
            "expires_at": "2025-02-01T00:00:00+07:00",
        }
    )

    with pytest.raises(ValidationError, match="đã hết hạn"):
        _service().activate(expired_key)


@pytest.mark.parametrize(
    "payload_update",
    [
        {"plan": "weekly"},
        {"v": "1"},
        {"paid_at": "2026-08-19"},
        {"expires_at": "không-phải-ngày"},
    ],
)
def test_rejects_invalid_signed_payload_fields(
    payload_update: dict[str, object],
) -> None:
    payload: dict[str, object] = {
        "v": 1,
        "customer_name": "Test Customer",
        "mac": "F0:68:E3:C4:D1:A1",
        "plan": "yearly",
        "paid_at": "2026-08-19T14:48:00+07:00",
        "expires_at": "2027-08-19T14:48:00+07:00",
    }
    payload.update(payload_update)

    with pytest.raises(ValidationError, match="không hợp lệ"):
        _service().activate(_signed_key(payload))


def test_rejects_signed_payload_with_missing_required_field() -> None:
    payload = {
        "v": 1,
        "customer_name": "Test Customer",
        "mac": "F0:68:E3:C4:D1:A1",
        "plan": "yearly",
        "paid_at": "2026-08-19T14:48:00+07:00",
    }

    with pytest.raises(ValidationError, match="không hợp lệ"):
        _service().activate(_signed_key(payload))


def test_accepts_lifetime_plan_payload() -> None:
    payload = {
        "v": 1,
        "customer_name": "Lifetime Customer",
        "mac": "F0:68:E3:C4:D1:A1",
        "plan": "lifetime",
        "paid_at": "2025-01-01T00:00:00+07:00",
        "expires_at": "2025-02-01T00:00:00+07:00",
    }

    result = _service().activate(_signed_key(payload))

    assert result.activated
    assert result.plan == "lifetime"
