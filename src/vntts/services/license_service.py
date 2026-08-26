"""Offline Ed25519 verification and local license state management."""

from __future__ import annotations

import base64
import binascii
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from vntts.utils.exceptions import ValidationError
from vntts.utils.machine_info import get_mac_address

# Development-only key pair.  This public key matches the private seed used
# by the test fixtures to sign sample licenses.
TEST_LICENSE_PUBLIC_KEY = "KpKH0Ng-3UJLEbEktxTBcWn4p_V1smDJ5K5kkhbbf4A"
CLOCK_ROLLBACK_MESSAGE = (
    "Phát hiện thời gian hệ thống không hợp lệ. "
    "Vui lòng kiểm tra lại ngày giờ của thiết bị."
)
LICENSE_REQUIRED_MESSAGE = "Vui lòng xác thực mã kích hoạt cho thiết bị này."
_STATE_FILENAME = "license.json"
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


class LicenseStatus(str, Enum):
    """Stable license states used by the UI access gate."""

    VALID = "VALID"
    NOT_ACTIVATED = "NOT_ACTIVATED"
    INVALID = "INVALID"
    WRONG_MACHINE = "WRONG_MACHINE"
    EXPIRED = "EXPIRED"
    CLOCK_ROLLBACK = "CLOCK_ROLLBACK"


class LicenseValidationError(ValidationError):
    """A validation failure carrying a machine-readable license state."""

    def __init__(self, message: str, status: LicenseStatus) -> None:
        super().__init__(message)
        self.status = status


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
    status: LicenseStatus = LicenseStatus.VALID


class LicenseService:
    """Verify and persist a signed, device-bound license without a server."""

    def __init__(
        self,
        storage_dir: Path | None = None,
        *,
        mac_provider: Callable[[], str] = get_mac_address,
        now_provider: Callable[[], datetime] = _local_now,
        public_key: str = TEST_LICENSE_PUBLIC_KEY,
    ) -> None:
        self._mac_provider = mac_provider
        self._now_provider = now_provider
        self._state_path = storage_dir / _STATE_FILENAME if storage_dir else None
        self._memory_state: dict[str, str] = {}
        try:
            self._public_key = Ed25519PublicKey.from_public_bytes(
                self._decode_base64url(public_key)
            )
        except (ValueError, TypeError) as exc:
            raise ValueError("Public key Ed25519 không hợp lệ.") from exc

    @property
    def state_path(self) -> Path | None:
        """Return the per-user state file path, when persistence is enabled."""

        return self._state_path

    def saved_key(self) -> str | None:
        """Return the locally stored key without treating it as activated."""

        state = self._load_state()
        key = state.get("license_key")
        return key if isinstance(key, str) and key.strip() else None

    def activate(self, key: str) -> LicenseActivationResult:
        """Verify a key and persist only the key and monotonic last-seen time."""

        result, now = self._verify(key)
        self._save_verified_state(key.strip(), now)
        return result

    def validate_saved(self) -> LicenseActivationResult:
        """Revalidate the saved key and advance the monotonic clock marker."""

        try:
            key = self.saved_key()
            if key is None:
                return LicenseActivationResult(
                    activated=False,
                    message=LICENSE_REQUIRED_MESSAGE,
                    status=LicenseStatus.NOT_ACTIVATED,
                )
            result, now = self._verify(key)
            self._save_verified_state(key, now)
            return result
        except LicenseValidationError as exc:
            return LicenseActivationResult(
                activated=False,
                message=str(exc),
                status=exc.status,
            )

    def require_valid(self) -> LicenseActivationResult:
        """Validate immediately before a licensed feature is used."""

        result = self.validate_saved()
        if not result.activated:
            raise LicenseValidationError(result.message, result.status)
        return result

    def _verify(self, key: str) -> tuple[LicenseActivationResult, datetime]:
        normalized = key.strip()
        parts = normalized.split(".")
        if len(parts) != 2 or not all(parts):
            raise LicenseValidationError(
                "Mã kích hoạt không đúng định dạng.", LicenseStatus.INVALID
            )

        try:
            payload_bytes = self._decode_base64url(parts[0])
            signature_bytes = self._decode_base64url(parts[1])
        except (ValueError, TypeError):
            raise LicenseValidationError(
                "Mã kích hoạt không đúng định dạng.", LicenseStatus.INVALID
            ) from None

        try:
            self._public_key.verify(signature_bytes, payload_bytes)
        except (InvalidSignature, ValueError):
            raise LicenseValidationError(
                "Mã kích hoạt không hợp lệ hoặc đã bị chỉnh sửa.",
                LicenseStatus.INVALID,
            ) from None

        payload = self._parse_payload(payload_bytes)
        license_mac = payload["mac"].upper().strip()
        machine_mac = self._mac_provider().upper().strip()
        if license_mac != machine_mac:
            raise LicenseValidationError(
                "Mã kích hoạt không thuộc thiết bị này.",
                LicenseStatus.WRONG_MACHINE,
            )

        paid_at = self._parse_datetime(payload["paid_at"])
        expires_at = self._parse_datetime(payload["expires_at"])
        if paid_at > expires_at:
            raise LicenseValidationError(
                "Mã kích hoạt không hợp lệ.", LicenseStatus.INVALID
            )

        now = self._aware_now()
        self._assert_clock_is_monotonic(now)
        if payload["plan"] != "lifetime" and now > expires_at:
            raise LicenseValidationError(
                "Mã kích hoạt đã hết hạn.", LicenseStatus.EXPIRED
            )

        return (
            LicenseActivationResult(
                activated=True,
                message="Xác thực mã kích hoạt thành công.",
                customer_name=payload["customer_name"],
                plan=payload["plan"],
                paid_at=payload["paid_at"],
                expires_at=payload["expires_at"],
                mac=payload["mac"],
                status=LicenseStatus.VALID,
            ),
            now,
        )

    def _aware_now(self) -> datetime:
        now = self._now_provider()
        if now.tzinfo is None or now.utcoffset() is None:
            now = now.astimezone()
        return now.astimezone(UTC)

    def _assert_clock_is_monotonic(self, now: datetime) -> None:
        state = self._load_state()
        stored = state.get("last_seen_time")
        if stored is None:
            return
        if not isinstance(stored, str):
            raise LicenseValidationError(
                "Dữ liệu bản quyền trên thiết bị không hợp lệ.",
                LicenseStatus.INVALID,
            )
        try:
            last_seen = self._parse_datetime(stored).astimezone(UTC)
        except ValidationError:
            raise LicenseValidationError(
                "Dữ liệu bản quyền trên thiết bị không hợp lệ.",
                LicenseStatus.INVALID,
            ) from None
        if now < last_seen:
            raise LicenseValidationError(
                CLOCK_ROLLBACK_MESSAGE, LicenseStatus.CLOCK_ROLLBACK
            )

    def _save_verified_state(self, key: str, now: datetime) -> None:
        # Re-read immediately before writing so a smaller timestamp can never
        # replace a newer value, even if state changed during verification.
        self._assert_clock_is_monotonic(now)
        state = {
            "license_key": key,
            "last_seen_time": now.astimezone(UTC).isoformat(),
        }
        if self._state_path is None:
            self._memory_state = state
            return
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = self._state_path.with_suffix(".tmp")
            temporary_path.write_text(
                json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            temporary_path.replace(self._state_path)
        except OSError as exc:
            raise LicenseValidationError(
                "Không thể lưu mã kích hoạt trên thiết bị.",
                LicenseStatus.INVALID,
            ) from exc

    def _load_state(self) -> dict[str, object]:
        if self._state_path is None:
            return dict(self._memory_state)
        if not self._state_path.exists():
            return {}
        try:
            state = json.loads(self._state_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LicenseValidationError(
                "Dữ liệu bản quyền trên thiết bị không hợp lệ.",
                LicenseStatus.INVALID,
            ) from exc
        if not isinstance(state, dict):
            raise LicenseValidationError(
                "Dữ liệu bản quyền trên thiết bị không hợp lệ.",
                LicenseStatus.INVALID,
            )
        return state

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
                encoded + padding, altchars=b"-_", validate=True
            )
        except binascii.Error as exc:
            raise ValueError("Base64URL không hợp lệ.") from exc

    @staticmethod
    def _parse_payload(payload_bytes: bytes) -> dict[str, object]:
        try:
            payload = json.loads(payload_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise LicenseValidationError(
                "Mã kích hoạt không hợp lệ.", LicenseStatus.INVALID
            ) from None
        if not isinstance(payload, dict) or not _REQUIRED_FIELDS.issubset(payload):
            raise LicenseValidationError(
                "Mã kích hoạt không hợp lệ.", LicenseStatus.INVALID
            )
        if type(payload["v"]) is not int or payload["v"] != 1:
            raise LicenseValidationError(
                "Mã kích hoạt không hợp lệ.", LicenseStatus.INVALID
            )
        for field in ("customer_name", "mac", "paid_at", "expires_at"):
            value = payload[field]
            if not isinstance(value, str) or not value.strip():
                raise LicenseValidationError(
                    "Mã kích hoạt không hợp lệ.", LicenseStatus.INVALID
                )
        if (
            not isinstance(payload["plan"], str)
            or payload["plan"] not in _SUPPORTED_PLANS
        ):
            raise LicenseValidationError(
                "Mã kích hoạt không hợp lệ.", LicenseStatus.INVALID
            )
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
