"""Future license-activation boundary."""

from __future__ import annotations

from dataclasses import dataclass

from vntts.utils.exceptions import ValidationError


@dataclass(frozen=True, slots=True)
class LicenseActivationResult:
    """Current placeholder result exposed to the UI."""

    activated: bool
    message: str


class LicenseService:
    """Placeholder interface for the future signed-license workflow."""

    def activate(self, key: str) -> LicenseActivationResult:
        """Accept a non-empty key without unlocking application features."""

        normalized = key.strip()
        if not normalized:
            raise ValidationError("Vui lòng nhập License Key.")

        # TODO: Verify signature, device binding, validity period and persist
        # activation state before enabling any licensed application features.
        return LicenseActivationResult(
            activated=False,
            message=(
                "License Key đã được ghi nhận. "
                "Chức năng xác thực sẽ được triển khai trong phiên bản sau."
            ),
        )
