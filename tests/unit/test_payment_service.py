"""Tests for payment API and mock boundaries."""

from __future__ import annotations

import json

import pytest

import vntts.services.payment_service as payment_module
from vntts.services.payment_service import PaymentRequest, PaymentService
from vntts.utils.exceptions import PaymentServiceError


@pytest.fixture
def payment_request() -> PaymentRequest:
    return PaymentRequest(
        name="Nguyễn Văn A",
        email="example@gmail.com",
        plan="monthly",
        mac_address="A1:B2:C3:D4:E5:F6",
    )


def test_mock_payment_service_returns_success_without_network(
    payment_request: PaymentRequest,
) -> None:
    service = PaymentService()

    response = service.request_payment(payment_request)

    assert service.is_mock_mode
    assert response.accepted
    assert response.mocked
    assert "Vui lòng kiểm tra email" in response.message
    assert payment_request.to_payload() == {
        "name": "Nguyễn Văn A",
        "email": "example@gmail.com",
        "plan": "monthly",
        "mac_address": "A1:B2:C3:D4:E5:F6",
    }


def test_posts_exact_json_payload(
    payment_request: PaymentRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class Response:
        status = 200

        def __enter__(self):  # type: ignore[no-untyped-def]
            return self

        def __exit__(self, *_args):  # type: ignore[no-untyped-def]
            return False

        @staticmethod
        def read() -> bytes:
            return b'{"success": true, "message": "OK"}'

    def fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        captured["request"] = request
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(payment_module.urllib.request, "urlopen", fake_urlopen)
    service = PaymentService(
        "https://example.com/api/payment/request",
        timeout_seconds=4,
    )

    response = service.request_payment(payment_request)

    request = captured["request"]
    assert request.get_method() == "POST"  # type: ignore[union-attr]
    assert json.loads(request.data.decode("utf-8")) == payment_request.to_payload()  # type: ignore[union-attr]
    assert captured["timeout"] == 4
    assert response.message == "OK"
    assert not response.mocked


def test_rejects_invalid_server_response(
    payment_request: PaymentRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        status = 200

        def __enter__(self):  # type: ignore[no-untyped-def]
            return self

        def __exit__(self, *_args):  # type: ignore[no-untyped-def]
            return False

        @staticmethod
        def read() -> bytes:
            return b"not-json"

    monkeypatch.setattr(
        payment_module.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: Response(),
    )

    with pytest.raises(PaymentServiceError, match="không hợp lệ"):
        PaymentService("https://example.com/api/payment/request").request_payment(
            payment_request
        )
