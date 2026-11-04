"""Offline license activation and information page."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
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
from vntts.utils.exceptions import ValidationError

_PLAN_LABELS = {
    "monthly": "1 tháng",
    "quarterly": "3 tháng",
    "semiannual": "6 tháng",
    "yearly": "1 năm",
    "lifetime": "Vĩnh viễn",
}


class PaymentPage(QWidget):
    """Activate a license and display its verified details."""

    license_activated = Signal(object)

    def __init__(
        self,
        license_service: LicenseService,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("paymentPage")
        self._license_service = license_service

        page_title = QLabel("Kích hoạt / Bản quyền", self)
        page_title.setProperty("role", "title")
        self.payment_help_button = QPushButton("Hướng dẫn", self)
        self.payment_help_button.setObjectName("paymentHelpButton")
        self.payment_help_button.setProperty("variant", "help")
        self.payment_help_button.setAccessibleName(
            "Mở hướng dẫn kích hoạt ứng dụng"
        )
        self.payment_help_button.setToolTip(
            "Xem hướng dẫn nhập mã kích hoạt"
        )
        self.payment_help_button.setFixedHeight(30)
        page_header = QHBoxLayout()
        page_header.setContentsMargins(0, 0, 0, 0)
        page_header.setSpacing(THEME.space_2)
        page_header.addWidget(page_title)
        page_header.addStretch()
        page_header.addWidget(self.payment_help_button)

        self.license_card = self._card()
        license_layout = self._card_layout(self.license_card)
        license_title = QLabel("Nhập mã kích hoạt", self.license_card)
        license_title.setObjectName("licenseSectionTitle")
        license_title.setProperty("role", "section")
        license_hint = QLabel(
            "Nhập mã kích hoạt được cung cấp theo hướng dẫn để xác thực "
            "và kích hoạt ứng dụng.",
            self.license_card,
        )
        license_hint.setObjectName("licenseSectionHint")
        license_hint.setProperty("role", "secondary")
        self.get_mac_button = QPushButton("Mã MAC", self.license_card)
        self.get_mac_button.setObjectName("getMacButton")
        self.get_mac_button.setAccessibleName("Lấy mã máy MAC")
        self.get_mac_button.setFixedHeight(30)
        license_header = QHBoxLayout()
        license_header.addWidget(license_title)
        license_header.addStretch()
        license_header.addWidget(self.get_mac_button)
        license_layout.addLayout(license_header)
        license_layout.addWidget(license_hint)
        license_layout.addWidget(self._divider(self.license_card))

        self.license_key_input = QLineEdit(self.license_card)
        self.license_key_input.setObjectName("licenseKeyInput")
        self.license_key_input.setPlaceholderText("Nhập mã kích hoạt")
        self.license_key_input.setAccessibleName("Mã kích hoạt")
        self.activate_button = QPushButton("Kích hoạt", self.license_card)
        self.activate_button.setObjectName("activateLicenseButton")
        self.activate_button.setProperty("variant", "primary")

        license_row = QHBoxLayout()
        license_row.setContentsMargins(0, 0, 0, 0)
        license_row.setSpacing(THEME.space_2)
        license_row.addWidget(self.license_key_input, 1)
        license_row.addWidget(self.activate_button)
        license_layout.addWidget(self._field_label("Mã kích hoạt", self.license_card))
        license_layout.addLayout(license_row)

        self.license_status_label = QLabel(self.license_card)
        self.license_status_label.setObjectName("licenseActivationStatusLabel")
        self.license_status_label.setWordWrap(True)
        self.license_status_label.hide()
        license_layout.addWidget(self.license_status_label)

        self.license_info_widget = QWidget(self.license_card)
        self.license_info_widget.setObjectName("licenseInformation")
        license_info_layout = QGridLayout(self.license_info_widget)
        license_info_layout.setContentsMargins(0, 0, 0, 0)
        license_info_layout.setHorizontalSpacing(THEME.space_3)
        license_info_layout.setVerticalSpacing(THEME.space_2)
        license_info_title = QLabel(
            "Thông tin bản quyền",
            self.license_info_widget,
        )
        license_info_title.setProperty("role", "section")
        license_info_layout.addWidget(license_info_title, 0, 0, 1, 2)
        self.license_plan_value = QLabel(self.license_info_widget)
        self.license_customer_value = QLabel(self.license_info_widget)
        self.license_paid_at_value = QLabel(self.license_info_widget)
        self.license_expires_at_value = QLabel(self.license_info_widget)
        license_values = (
            ("Gói", self.license_plan_value),
            ("Khách hàng", self.license_customer_value),
            ("Ngày thanh toán", self.license_paid_at_value),
            ("Hết hạn", self.license_expires_at_value),
        )
        for row, (label, value_widget) in enumerate(license_values, start=1):
            field_label = self._field_label(label, self.license_info_widget)
            if value_widget is self.license_customer_value:
                self.license_customer_label = field_label
            license_info_layout.addWidget(
                field_label,
                row,
                0,
            )
            license_info_layout.addWidget(value_widget, row, 1)
        license_info_layout.setColumnStretch(1, 1)
        self.license_info_widget.hide()
        license_layout.addWidget(self.license_info_widget)

        cards = QVBoxLayout()
        cards.setContentsMargins(0, 0, 0, 0)
        cards.setSpacing(THEME.space_3)
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
        layout.addLayout(page_header)
        layout.addWidget(self._divider(self))
        layout.addLayout(content_row)
        layout.addStretch()

        self.activate_button.clicked.connect(self._activate_license)
        self.payment_help_button.clicked.connect(self._show_payment_help)
        self.get_mac_button.clicked.connect(self._show_machine_mac)

    def _show_machine_mac(self) -> None:
        """Display the machine identifier only when requested."""

        dialog = QDialog(self)
        dialog.setObjectName("machineMacDialog")
        dialog.setWindowTitle("Mã máy (MAC)")
        dialog.setMinimumWidth(360)
        dialog_layout = QVBoxLayout(dialog)
        machine_title = self._field_label("MAC", dialog)
        self.machine_mac_input = QLineEdit(dialog)
        self.machine_mac_input.setObjectName("machineMacInput")
        self.machine_mac_input.setReadOnly(True)
        self.machine_mac_input.setAccessibleName("Mã máy (MAC)")
        self.machine_mac_input.setFixedHeight(30)
        self.machine_mac_input.setToolTip("Gửi mã máy này khi mua bản quyền")
        machine_title.setBuddy(self.machine_mac_input)
        self.copy_mac_button = QPushButton("Sao chép", dialog)
        self.copy_mac_button.setFixedHeight(30)
        self.copy_mac_button.setObjectName("copyMacButton")
        self.copy_mac_button.setAccessibleName("Sao chép mã máy MAC")
        machine_row = QHBoxLayout()
        machine_row.setContentsMargins(0, 0, 0, 0)
        machine_row.setSpacing(THEME.space_2)
        machine_row.addWidget(machine_title)
        machine_row.addWidget(self.machine_mac_input)
        machine_row.addWidget(self.copy_mac_button)
        dialog_layout.addLayout(machine_row)
        self.machine_status_label = QLabel(dialog)
        self.machine_status_label.setWordWrap(True)
        self.machine_status_label.hide()
        dialog_layout.addWidget(self.machine_status_label)
        try:
            machine_mac = self._license_service.machine_mac()
            if not machine_mac:
                raise ValueError("Không đọc được mã máy.")
            self.machine_mac_input.setText(machine_mac)
        except (ValueError, OSError, ValidationError):
            self.machine_mac_input.setPlaceholderText("Không đọc được mã máy")
            self.copy_mac_button.setEnabled(False)
            self._show_status(
                self.machine_status_label,
                "Không thể lấy mã MAC. Vui lòng mở lại ứng dụng hoặc liên hệ hỗ trợ.",
                "error",
            )

        close_button = QPushButton("Đóng", dialog)
        close_button.clicked.connect(dialog.accept)
        dialog_layout.addWidget(close_button)
        self.copy_mac_button.clicked.connect(self._copy_machine_mac)
        dialog.exec()

    def _copy_machine_mac(self) -> None:
        """Copy only the identifier so it can be sent for license issuance."""

        mac = self.machine_mac_input.text()
        if not mac:
            return
        QApplication.clipboard().setText(mac)
        self._show_status(
            self.machine_status_label, "Đã sao chép mã máy.", "success"
        )

    def _show_payment_help(self) -> None:
        """Explain offline license activation."""

        QMessageBox.information(
            self,
            "Hướng dẫn kích hoạt",
            "Kích hoạt ứng dụng\n"
            "Nếu chưa có mã kích hoạt, bấm 'Mã MAC', sao chép MAC và gửi cho "
            "bộ phận hỗ trợ khi mua bản quyền.\n\n"
            "1. Sao chép đầy đủ mã kích hoạt đã nhận.\n"
            "2. Dán mã vào ô 'Mã kích hoạt' và bấm 'Kích hoạt'.\n"
            "3. Khi xác thực thành công, kiểm tra thông tin gói, khách hàng "
            "và ngày hết hạn. Trang 'Tạo giọng nói' và 'Nhân bản giọng' sẽ "
            "được mở khóa.\n\n"
            "Nếu mã báo hết hạn hoặc không hợp lệ, hãy kiểm tra lại mã và "
            "liên hệ bộ phận hỗ trợ. Không thay đổi ngày giờ hệ "
            "thống trong quá trình sử dụng license.",
            QMessageBox.StandardButton.Ok,
        )

    def apply_saved_license(self, result: LicenseActivationResult) -> None:
        """Reflect the startup license check without verifying it a second time."""

        try:
            saved_key = self._license_service.saved_key()
        except ValidationError:
            saved_key = None
        if saved_key:
            self.license_key_input.setText(saved_key)
        self._clear_license_information()
        if result.activated:
            self._show_status(
                self.license_status_label,
                f"✓ {result.message}",
                "success",
            )
            self._show_license_information(result)
        elif result.message:
            self._show_status(
                self.license_status_label,
                result.message,
                "error",
            )

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

    def _activate_license(self) -> None:
        self._clear_license_information()
        key = self.license_key_input.text().strip()
        if not key:
            self._show_status(
                self.license_status_label,
                "Vui lòng nhập mã kích hoạt.",
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
        if result.activated:
            self._show_status(
                self.license_status_label,
                f"✓ {result.message}",
                "success",
            )
            self._show_license_information(result)
            self.license_activated.emit(result)
            return
        self._show_status(
            self.license_status_label,
            result.message,
            "neutral",
        )

    def _show_license_information(
        self,
        result: LicenseActivationResult,
    ) -> None:
        self.license_plan_value.setText(
            _PLAN_LABELS.get(result.plan or "", "")
        )
        self.license_customer_value.setText(result.customer_name or "")
        has_customer = bool(result.customer_name and result.customer_name.strip())
        self.license_customer_label.setVisible(has_customer)
        self.license_customer_value.setVisible(has_customer)
        self.license_paid_at_value.setText(
            self._format_license_date(result.paid_at)
        )
        expires_text = (
            "Không thời hạn"
            if result.plan == "lifetime"
            else self._format_license_date(result.expires_at)
        )
        self.license_expires_at_value.setText(expires_text)
        self.license_info_widget.show()

    def _clear_license_information(self) -> None:
        self.license_info_widget.hide()
        self.license_plan_value.clear()
        self.license_customer_value.clear()
        self.license_paid_at_value.clear()
        self.license_expires_at_value.clear()

    @staticmethod
    def _format_license_date(value: str | None) -> str:
        if not value:
            return ""
        return datetime.fromisoformat(value).strftime("%d/%m/%Y")

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
