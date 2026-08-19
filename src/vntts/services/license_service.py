"""Offline Ed25519 verification for device-bound license keys."""

from __future__ import annotations

import base64
import binascii
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from vntts.utils.exceptions import ValidationError
from vntts.utils.machine_info import get_mac_address

TEST_LICENSE_PUBLIC_KEY = "KpKH0Ng-3UJLEbEktxTBcWn4p_V1smDJ5K5kkhbbf4A"
_REQUIRED_FIELDS = {
    "v",
    "customer_name",
    "mac",
    "plan",
    "paid_at",
    "expires_at",
}
_SUPPORTED_PLANS = {
    "monthly",
    "quarterly",
    "semiannual",
    "yearly",
    "lifetime",
}


def _local_now() -> datetime:
    return datetime.now().astimezone()


@dataclass(frozen=True, slots=True)
class LicenseActivationResult:
    """Verified license details exposed to the presentation layer."""

    activated: bool
    message: str
    customer_name: str | None = None
    plan: str | None = None
    paid_at: str | None = None
    expires_at: str | None = None
    mac: str | None = None


class LicenseService:
    """Verify signed license payloads without contacting a server."""

    def __init__(
        self,
        *,
        mac_provider: Callable[[], str] = get_mac_address,
        now_provider: Callable[[], datetime] = _local_now,
        public_key: str = TEST_LICENSE_PUBLIC_KEY,
    ) -> None:
        self._mac_provider = mac_provider
        self._now_provider = now_provider
        try:
            self._public_key = Ed25519PublicKey.from_public_bytes(
                self._decode_base64url(public_key)
            )
        except (ValueError, TypeError) as exc:
            raise ValueError("Public key Ed25519 không hợp lệ.") from exc

    def activate(self, key: str) -> LicenseActivationResult:
        """Verify signature, payload, device binding and expiration."""

        normalized = key.strip()
        parts = normalized.split(".")
        if len(parts) != 2 or not all(parts):
            raise ValidationError("Mã kích hoạt không đúng định dạng.")

        try:
            payload_bytes = self._decode_base64url(parts[0])
            signature_bytes = self._decode_base64url(parts[1])
        except (ValueError, TypeError):
            raise ValidationError("Mã kích hoạt không đúng định dạng.") from None

        try:
            self._public_key.verify(signature_bytes, payload_bytes)
        except (InvalidSignature, ValueError):
            raise ValidationError(
                "Mã kích hoạt không hợp lệ hoặc đã bị chỉnh sửa."
            ) from None

        payload = self._parse_payload(payload_bytes)
        license_mac = payload["mac"].upper().strip()
        machine_mac = self._mac_provider().upper().strip()
        if license_mac != machine_mac:
            raise ValidationError("Mã kích hoạt không thuộc thiết bị này.")

        paid_at = self._parse_datetime(payload["paid_at"])
        expires_at = self._parse_datetime(payload["expires_at"])
        if paid_at > expires_at:
            raise ValidationError("Mã kích hoạt không hợp lệ.")
        now = self._now_provider()
        if now.tzinfo is None or now.utcoffset() is None:
            now = now.astimezone()
        if payload["plan"] != "lifetime" and now > expires_at:
            raise ValidationError("Mã kích hoạt đã hết hạn.")

        return LicenseActivationResult(
            activated=True,
            message="Xác thực mã kích hoạt thành công.",
            customer_name=payload["customer_name"],
            plan=payload["plan"],
            paid_at=payload["paid_at"],
            expires_at=payload["expires_at"],
            mac=payload["mac"],
        )

    @staticmethod
    def _decode_base64url(value: str) -> bytes:
        if not re.fullmatch(r"[A-Za-z0-9_-]+={0,2}", value):
            raise ValueError("Base64URL không hợp lệ.")
        try:
            encoded = value.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ValueError("Base64URL không hợp lệ.") from exc
        padding = b"=" * (-len(encoded) % 4)
        try:
            return base64.b64decode(
                encoded + padding,
                altchars=b"-_",
                validate=True,
            )
        except binascii.Error as exc:
            raise ValueError("Base64URL không hợp lệ.") from exc

    @staticmethod
    def _parse_payload(payload_bytes: bytes) -> dict[str, object]:
        try:
            payload = json.loads(payload_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValidationError("Mã kích hoạt không hợp lệ.") from None
        if not isinstance(payload, dict) or not _REQUIRED_FIELDS.issubset(payload):
            raise ValidationError("Mã kích hoạt không hợp lệ.")
        if type(payload["v"]) is not int or payload["v"] != 1:
            raise ValidationError("Mã kích hoạt không hợp lệ.")
        for field in ("customer_name", "mac", "paid_at", "expires_at"):
            value = payload[field]
            if not isinstance(value, str) or not value.strip():
                raise ValidationError("Mã kích hoạt không hợp lệ.")
        if (
            not isinstance(payload["plan"], str)
            or payload["plan"] not in _SUPPORTED_PLANS
        ):
            raise ValidationError("Mã kích hoạt không hợp lệ.")
        return payload

    @staticmethod
    def _parse_datetime(value: object) -> datetime:
        if not isinstance(value, str):
            raise ValidationError("Mã kích hoạt không hợp lệ.")
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            raise ValidationError("Mã kích hoạt không hợp lệ.") from None
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValidationError("Mã kích hoạt không hợp lệ.")
        return parsed
