"""Payment request and placeholder license activation page."""

from __future__ import annotations

import re

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from vntts.config.theme import THEME
from vntts.services.license_service import (
    LicenseActivationResult,
    LicenseService,
)
from vntts.services.payment_service import (
    PaymentRequest,
    PaymentResponse,
    PaymentService,
)
from vntts.ui.controls import ChevronComboBox
from vntts.utils.exceptions import ValidationError
from vntts.utils.machine_info import get_mac_address
from vntts.utils.worker import TaskWorker

_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class PaymentPage(QWidget):
    """Collect payment details and expose future license activation."""

    def __init__(
        self,
        payment_service: PaymentService,
        license_service: LicenseService,
        *,
        mac_address: str | None = None,
        thread_pool: QThreadPool | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("paymentPage")
        self._payment_service = payment_service
        self._license_service = license_service
        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        self._payment_worker: TaskWorker | None = None

        page_title = QLabel("Thanh toán / Bản quyền", self)
        page_title.setProperty("role", "title")

        self.payment_card = self._card()
        payment_layout = self._card_layout(self.payment_card)
        payment_title = QLabel("Yêu cầu thanh toán", self.payment_card)
        payment_title.setProperty("role", "section")
        payment_hint = QLabel(
            "Gửi thông tin để nhận hướng dẫn thanh toán qua email.",
            self.payment_card,
        )
        payment_hint.setProperty("role", "secondary")
        payment_layout.addWidget(payment_title)
        payment_layout.addWidget(payment_hint)
        payment_layout.addWidget(self._divider(self.payment_card))

        form = QGridLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(THEME.space_3)
        form.setVerticalSpacing(THEME.space_2)

        self.plan_combo = ChevronComboBox(self.payment_card)
        self.plan_combo.setObjectName("paymentPlanCombo")
        self.plan_combo.setAccessibleName("Gói thanh toán")
        self.plan_combo.addItem("Chọn gói", None)
        self.plan_combo.addItem("1 tháng", "monthly")
        self.plan_combo.addItem("1 năm", "yearly")

        self.name_input = QLineEdit(self.payment_card)
        self.name_input.setObjectName("paymentNameInput")
        self.name_input.setPlaceholderText("Nguyễn Văn A")
        self.name_input.setAccessibleName("Họ và tên")

        self.email_input = QLineEdit(self.payment_card)
        self.email_input.setObjectName("paymentEmailInput")
        self.email_input.setPlaceholderText("example@gmail.com")
        self.email_input.setAccessibleName("Email")

        self.mac_input = QLineEdit(self.payment_card)
        self.mac_input.setObjectName("paymentMacAddress")
        self.mac_input.setReadOnly(True)
        self.mac_input.setAccessibleName("Địa chỉ MAC của máy")
        self.mac_input.setText(mac_address or get_mac_address())

        self.copy_mac_button = QPushButton("Sao chép", self.payment_card)
        self.copy_mac_button.setObjectName("copyMacButton")
        self.copy_mac_button.setProperty("variant", "secondary")
        self.copy_mac_button.setAccessibleName("Sao chép địa chỉ MAC")

        mac_row = QHBoxLayout()
        mac_row.setContentsMargins(0, 0, 0, 0)
        mac_row.setSpacing(THEME.space_2)
        mac_row.addWidget(self.mac_input, 1)
        mac_row.addWidget(self.copy_mac_button)

        self._add_field(form, 0, "Chọn gói", self.plan_combo)
        self._add_field(form, 1, "Họ và tên", self.name_input)
        self._add_field(form, 2, "Email", self.email_input)
        mac_label = self._field_label("Địa chỉ MAC của máy", self.payment_card)
        form.addWidget(mac_label, 3, 0)
        form.addLayout(mac_row, 3, 1)
        form.setColumnStretch(1, 1)
        payment_layout.addLayout(form)

        self.send_button = QPushButton(
            "Gửi yêu cầu thanh toán",
            self.payment_card,
        )
        self.send_button.setObjectName("sendPaymentRequestButton")
        self.send_button.setProperty("variant", "primary")
        self.send_button.setAccessibleName("Gửi yêu cầu thanh toán")

        self.payment_status_label = QLabel(self.payment_card)
        self.payment_status_label.setObjectName("paymentStatusLabel")
        self.payment_status_label.setWordWrap(True)
        self.payment_status_label.hide()

        payment_actions = QHBoxLayout()
        payment_actions.setContentsMargins(0, 0, 0, 0)
        payment_actions.addStretch()
        payment_actions.addWidget(self.send_button)
        payment_layout.addWidget(self.payment_status_label)
        payment_layout.addLayout(payment_actions)

        self.license_card = self._card()
        license_layout = self._card_layout(self.license_card)
        license_title = QLabel("Nhập License Key", self.license_card)
        license_title.setProperty("role", "section")
        license_hint = QLabel(
            "Chức năng xác thực và mở khóa sẽ được bổ sung trong phiên bản sau.",
            self.license_card,
        )
        license_hint.setProperty("role", "secondary")
        license_layout.addWidget(license_title)
        license_layout.addWidget(license_hint)
        license_layout.addWidget(self._divider(self.license_card))

        self.license_key_input = QLineEdit(self.license_card)
        self.license_key_input.setObjectName("licenseKeyInput")
        self.license_key_input.setPlaceholderText("Nhập License Key")
        self.license_key_input.setAccessibleName("License Key")
        self.activate_button = QPushButton("Kích hoạt", self.license_card)
        self.activate_button.setObjectName("activateLicenseButton")
        self.activate_button.setProperty("variant", "primary")

        license_row = QHBoxLayout()
        license_row.setContentsMargins(0, 0, 0, 0)
        license_row.setSpacing(THEME.space_2)
        license_row.addWidget(self.license_key_input, 1)
        license_row.addWidget(self.activate_button)
        license_layout.addWidget(self._field_label("License Key", self.license_card))
        license_layout.addLayout(license_row)

        self.license_status_label = QLabel(self.license_card)
        self.license_status_label.setObjectName("licenseActivationStatusLabel")
        self.license_status_label.setWordWrap(True)
        self.license_status_label.hide()
        license_layout.addWidget(self.license_status_label)

        cards = QVBoxLayout()
        cards.setContentsMargins(0, 0, 0, 0)
        cards.setSpacing(THEME.space_3)
        cards.addWidget(self.payment_card)
        cards.addWidget(self.license_card)
        cards_container = QWidget(self)
        cards_container.setMaximumWidth(THEME.content_reading_width)
        cards_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        cards_container.setLayout(cards)

        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.addStretch(1)
        content_row.addWidget(cards_container, 100)
        content_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            THEME.space_5,
            THEME.space_4,
            THEME.space_5,
            THEME.space_5,
        )
        layout.setSpacing(THEME.space_3)
        layout.addWidget(page_title)
        layout.addWidget(self._divider(self))
        layout.addLayout(content_row)
        layout.addStretch()

        self.copy_mac_button.clicked.connect(self._copy_mac_address)
        self.send_button.clicked.connect(self._submit_payment_request)
        self.activate_button.clicked.connect(self._activate_license)

    @staticmethod
    def _card() -> QFrame:
        card = QFrame()
        card.setProperty("card", True)
        card.setMaximumWidth(THEME.content_reading_width)
        card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        return card

    @staticmethod
    def _card_layout(card: QFrame) -> QVBoxLayout:
        layout = QVBoxLayout(card)
        layout.setContentsMargins(
            THEME.space_4,
            THEME.space_4,
            THEME.space_4,
            THEME.space_4,
        )
        layout.setSpacing(THEME.space_3)
        return layout

    @staticmethod
    def _divider(parent: QWidget) -> QFrame:
        divider = QFrame(parent)
        divider.setObjectName("sectionDivider")
        divider.setFrameShape(QFrame.Shape.NoFrame)
        divider.setFixedHeight(int(THEME.control_stroke_width))
        return divider

    @staticmethod
    def _field_label(text: str, parent: QWidget) -> QLabel:
        label = QLabel(text, parent)
        label.setObjectName("fieldLabel")
        return label

    def _add_field(
        self,
        layout: QGridLayout,
        row: int,
        label: str,
        widget: QWidget,
    ) -> None:
        layout.addWidget(self._field_label(label, self.payment_card), row, 0)
        layout.addWidget(widget, row, 1)

    def _copy_mac_address(self) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(self.mac_input.text())
        self._show_status(
            self.payment_status_label,
            "Đã sao chép địa chỉ MAC.",
            "success",
        )

    def _submit_payment_request(self) -> None:
        try:
            payment = self._validated_payment_request()
        except ValidationError as exc:
            self._show_status(self.payment_status_label, str(exc), "error")
            return

        self._set_payment_loading(True)
        worker = TaskWorker(self._payment_service.request_payment, payment)
        self._payment_worker = worker
        worker.signals.result.connect(self._payment_succeeded)
        worker.signals.error.connect(self._payment_failed)
        worker.signals.finished.connect(self._payment_finished)
        self._thread_pool.start(worker)

    def _validated_payment_request(self) -> PaymentRequest:
        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        plan = self.plan_combo.currentData()
        if not name:
            raise ValidationError("Vui lòng nhập họ và tên.")
        if not email:
            raise ValidationError("Vui lòng nhập email.")
        if not _EMAIL_PATTERN.fullmatch(email):
            raise ValidationError("Email không đúng định dạng.")
        if plan not in {"monthly", "yearly"}:
            raise ValidationError("Vui lòng chọn gói thanh toán.")
        return PaymentRequest(
            name=name,
            email=email,
            plan=str(plan),
            mac_address=self.mac_input.text(),
        )

    def _payment_succeeded(self, response: object) -> None:
        if not isinstance(response, PaymentResponse):
            self._payment_failed("Phản hồi thanh toán không hợp lệ.")
            return
        self._show_status(
            self.payment_status_label,
            response.message,
            "success",
        )

    def _payment_failed(self, message: str) -> None:
        self._show_status(self.payment_status_label, message, "error")

    def _payment_finished(self) -> None:
        self._set_payment_loading(False)
        self._payment_worker = None

    def _set_payment_loading(self, loading: bool) -> None:
        self.send_button.setEnabled(not loading)
        self.send_button.setText(
            "Đang gửi..." if loading else "Gửi yêu cầu thanh toán"
        )
        self.plan_combo.setEnabled(not loading)
        self.name_input.setEnabled(not loading)
        self.email_input.setEnabled(not loading)
        if loading:
            self._show_status(
                self.payment_status_label,
                "Đang gửi yêu cầu thanh toán...",
                "busy",
            )

    def _activate_license(self) -> None:
        key = self.license_key_input.text().strip()
        if not key:
            self._show_status(
                self.license_status_label,
                "Vui lòng nhập License Key.",
                "error",
            )
            return
        try:
            result = self._license_service.activate(key)
        except ValidationError as exc:
            self._show_status(self.license_status_label, str(exc), "error")
            return
        self._show_activation_result(result)

    def _show_activation_result(self, result: LicenseActivationResult) -> None:
        self._show_status(
            self.license_status_label,
            result.message,
            "success" if result.activated else "neutral",
        )

    @staticmethod
    def _show_status(label: QLabel, message: str, state: str) -> None:
        colors = {
            "busy": THEME.info,
            "success": THEME.success,
            "error": THEME.error,
            "neutral": THEME.text_secondary,
        }
        label.setStyleSheet(
            f"color: {colors[state]}; "
            f"font-size: {THEME.font_size_caption}px;"
        )
        label.setText(message)
        label.show()
