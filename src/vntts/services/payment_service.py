"""Payment-request boundary with an explicit development mock mode."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from vntts.utils.exceptions import PaymentServiceError

PAYMENT_REQUEST_PATH = "/payment/request"
PAYMENT_SUCCESS_MESSAGE = (
    "Yêu cầu thanh toán đã được gửi.\n"
    "Vui lòng kiểm tra email để nhận hướng dẫn thanh toán."
)


@dataclass(frozen=True, slots=True)
class PaymentRequest:
    """Data accepted by the payment-request API."""

    name: str
    email: str
    plan: str
    price: int
    mac: str

    def to_payload(self) -> dict[str, str | int]:
        """Return the JSON-compatible server payload."""

        return {
            "name": self.name,
            "email": self.email,
            "plan": self.plan,
            "price": self.price,
            "mac": self.mac,
        }


@dataclass(frozen=True, slots=True)
class PaymentResponse:
    """Normalized response returned to the presentation layer."""

    accepted: bool
    message: str
    mocked: bool = False


class PaymentService:
    """Submit payment requests, or return a clear mock while API is absent."""

    def __init__(self, endpoint: str = "", timeout_seconds: float = 10) -> None:
        self._endpoint = endpoint.strip()
        self._timeout_seconds = timeout_seconds

    @property
    def is_mock_mode(self) -> bool:
        """Return whether requests are handled locally without network I/O."""

        return not self._endpoint

    def request_payment(self, payment: PaymentRequest) -> PaymentResponse:
        """POST a payment request or provide the development mock response."""

        if self.is_mock_mode:
            return PaymentResponse(True, PAYMENT_SUCCESS_MESSAGE, mocked=True)

        body = json.dumps(payment.to_payload(), ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self._endpoint,
            data=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self._timeout_seconds,
            ) as response:
                status = int(getattr(response, "status", 200))
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raise PaymentServiceError(
                f"Máy chủ từ chối yêu cầu thanh toán (HTTP {exc.code})."
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise PaymentServiceError(
                "Không thể kết nối máy chủ thanh toán. Vui lòng thử lại."
            ) from exc

        if not 200 <= status < 300:
            raise PaymentServiceError(
                f"Máy chủ từ chối yêu cầu thanh toán (HTTP {status})."
            )
        try:
            payload = json.loads(response_body) if response_body else {}
        except json.JSONDecodeError as exc:
            raise PaymentServiceError(
                "Phản hồi từ máy chủ thanh toán không hợp lệ."
            ) from exc
        if not isinstance(payload, dict):
            raise PaymentServiceError(
                "Phản hồi từ máy chủ thanh toán không hợp lệ."
            )
        accepted = bool(payload.get("success", True))
        message = str(payload.get("message") or PAYMENT_SUCCESS_MESSAGE)
        if not accepted:
            raise PaymentServiceError(message)
        return PaymentResponse(True, message)
