"""Company contact information page backed by application settings."""

from __future__ import annotations

import html
import sys
from pathlib import Path
from urllib.parse import quote

from PySide6.QtCore import QLineF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from vntts.config.theme import THEME


def _company_logo_path() -> Path:
    """Return the company logo path in source and frozen builds."""

    bundle_root = Path(
        getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3])
    )
    return bundle_root / "resources" / "image" / "logo-GPHI.webp"


class ContactPage(QWidget):
    """Display company and technical-support contact details."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("contactPage")

        page_title = QLabel("Liên hệ", self)
        page_title.setProperty("role", "title")
        page_divider = self._divider()

        self.card = QFrame(self)
        self.card.setObjectName("contactCard")
        self.card.setProperty("card", True)
        self.card.setMaximumWidth(THEME.content_reading_width)
        self.card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        company_icon = self._company_logo_label()
        company_icon.setObjectName("contactCompanyIcon")
        self.company_name_label = QLabel("Chưa cập nhật", self.card)
        self.company_name_label.setObjectName("contactCompanyName")
        self.company_name_label.setProperty("role", "section")
        self.company_name_label.setWordWrap(True)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(THEME.space_3)
        header.addWidget(company_icon)
        header.addWidget(self.company_name_label, 1)

        section_title = QLabel("THÔNG TIN LIÊN HỆ", self.card)
        section_title.setObjectName("contactSectionTitle")
        section_title.setStyleSheet(
            f"color: {THEME.accent}; "
            f"font-size: {THEME.font_size_caption}px; font-weight: 600;"
        )

        details = QGridLayout()
        details.setContentsMargins(0, 0, 0, 0)
        details.setHorizontalSpacing(THEME.space_3)
        details.setVerticalSpacing(THEME.space_3)
        address_cell, self.address_label = self._detail_cell(
            "Địa chỉ",
            "location",
            "contactAddress",
        )
        phone_cell, self.phone_label = self._detail_cell(
            "Điện thoại",
            "phone",
            "contactPhone",
        )
        email_cell, self.email_label = self._detail_cell(
            "Email",
            "email",
            "contactEmail",
        )
        website_cell, self.website_label = self._detail_cell(
            "Website",
            "website",
            "contactWebsite",
        )
        support_cell, self.support_email_label = self._detail_cell(
            "Hỗ trợ kỹ thuật",
            "support",
            "contactTechnicalSupportEmail",
        )
        details.addWidget(address_cell, 0, 0, 1, 3)
        details.addWidget(self._divider(), 1, 0, 1, 3)
        details.addWidget(phone_cell, 2, 0)
        details.addWidget(self._divider(vertical=True), 2, 1)
        details.addWidget(email_cell, 2, 2)
        details.addWidget(self._divider(), 3, 0, 1, 3)
        details.addWidget(website_cell, 4, 0)
        details.addWidget(self._divider(vertical=True), 4, 1)
        details.addWidget(support_cell, 4, 2)
        details.setColumnStretch(0, 1)
        details.setColumnStretch(2, 1)

        self.license_toggle_button = QPushButton(
            "ĐIỀU KHOẢN && GIẤY PHÉP",
            self.card,
        )
        self.license_toggle_button.setObjectName("contactLicenseToggle")
        self.license_toggle_button.setCheckable(True)
        self.license_toggle_button.setAccessibleName(
            "Hiển thị nội dung giấy phép"
        )
        self.license_toggle_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.license_toggle_button.setStyleSheet(
            f"color: {THEME.accent}; "
            f"font-size: {THEME.font_size_caption - 1}px; font-weight: 600; "
            "text-align: right; background: transparent; border: none; "
            "padding: 0;"
        )
        self.license_link_label = QLabel(self.card)
        self.license_link_label.setObjectName("contactLicenseLink")
        self.license_link_label.setTextFormat(Qt.TextFormat.PlainText)
        self.license_link_label.setOpenExternalLinks(False)
        self.license_link_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.license_link_label.setWordWrap(True)
        self.license_link_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        self.license_link_label.setStyleSheet(
            f"color: {THEME.text_secondary}; "
            f"font-size: {THEME.font_size_caption - 1}px;"
        )
        self.license_link_label.setText(
            "Phần mềm này sử dụng Qt/PySide6 và các thành phần "
            "mã nguồn mở khác. "
            "Thông tin giấy phép được cung cấp trong thư mục "
            "_internal/licenses"
        )
        self.license_link_label.hide()
        self.license_toggle_button.toggled.connect(
            self.license_link_label.setVisible
        )

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(
            THEME.space_4,
            THEME.space_4,
            THEME.space_4,
            THEME.space_4,
        )
        card_layout.setSpacing(THEME.space_3)
        card_layout.addLayout(header)
        card_layout.addWidget(self._divider())
        card_layout.addWidget(section_title)
        card_layout.addLayout(details)
        card_layout.addWidget(self._divider())
        card_layout.addWidget(
            self.license_toggle_button,
            0,
            Qt.AlignmentFlag.AlignRight,
        )
        card_layout.addWidget(self.license_link_label)

        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.addStretch(1)
        content_row.addWidget(self.card, 100)
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
        layout.addWidget(page_divider)
        layout.addLayout(content_row)
        layout.addStretch()

    def set_info(
        self,
        manufacturer: str,
        address: str,
        phone: str,
        support_email: str,
        website: str,
    ) -> None:
        """Refresh displayed values from ``Settings.application``."""

        self._set_plain_text(self.company_name_label, manufacturer)
        self._set_plain_text(self.address_label, address)
        self._set_link(self.phone_label, phone, "tel")
        self._set_link(self.email_label, support_email, "mailto")
        self._set_link(self.website_label, website, "website")
        self._set_link(self.support_email_label, support_email, "mailto")

    def _detail_cell(
        self,
        title: str,
        icon: str,
        object_name: str,
    ) -> tuple[QWidget, QLabel]:
        cell = QWidget(self.card)
        icon_label = self._icon_label(
            icon,
            THEME.space_6 + THEME.space_2,
            THEME.icon_size,
        )
        title_label = QLabel(title, cell)
        title_label.setObjectName("fieldLabel")
        value_label = QLabel("Chưa cập nhật", cell)
        value_label.setObjectName(object_name)
        value_label.setWordWrap(True)
        self._set_muted(value_label)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(THEME.space_1)
        text_layout.addWidget(title_label)
        text_layout.addWidget(value_label)

        layout = QHBoxLayout(cell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(THEME.space_3)
        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(text_layout, 1)
        return cell, value_label

    def _icon_label(
        self,
        icon: str,
        container_size: int,
        icon_size: int,
    ) -> QLabel:
        label = QLabel(self.card)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFixedSize(container_size, container_size)
        label.setStyleSheet(
            f"background: {THEME.accent_soft}; "
            f"border-radius: {container_size // 2}px;"
        )
        label.setPixmap(self._draw_icon(icon, icon_size))
        return label

    def _company_logo_label(self) -> QLabel:
        size = THEME.space_6 + THEME.space_4
        label = QLabel(self.card)
        label.setFixedSize(size, size)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo = QPixmap(str(_company_logo_path()))
        if logo.isNull():
            return self._icon_label("building", size, THEME.space_6)
        label.setPixmap(
            logo.scaled(
                size,
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        return label

    @staticmethod
    def _draw_icon(kind: str, size: int) -> QPixmap:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(THEME.accent))
        pen.setWidthF(THEME.control_stroke_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        unit = float(size)

        if kind == "building":
            painter.drawRoundedRect(
                QRectF(unit * 0.31, unit * 0.12, unit * 0.38, unit * 0.74),
                unit * 0.04,
                unit * 0.04,
            )
            painter.drawRect(
                QRectF(unit * 0.14, unit * 0.42, unit * 0.17, unit * 0.44)
            )
            painter.drawRect(
                QRectF(unit * 0.69, unit * 0.34, unit * 0.17, unit * 0.52)
            )
            for x_position in (0.40, 0.55):
                for y_position in (0.25, 0.41, 0.57):
                    painter.drawRect(
                        QRectF(
                            unit * x_position,
                            unit * y_position,
                            unit * 0.06,
                            unit * 0.06,
                        )
                    )
            painter.drawRect(
                QRectF(unit * 0.45, unit * 0.70, unit * 0.10, unit * 0.16)
            )
            painter.drawLine(
                QLineF(unit * 0.08, unit * 0.87, unit * 0.92, unit * 0.87)
            )
        elif kind == "location":
            path = QPainterPath()
            path.moveTo(unit * 0.50, unit * 0.90)
            path.cubicTo(
                unit * 0.43,
                unit * 0.78,
                unit * 0.22,
                unit * 0.58,
                unit * 0.22,
                unit * 0.40,
            )
            path.cubicTo(
                unit * 0.22,
                unit * 0.20,
                unit * 0.34,
                unit * 0.10,
                unit * 0.50,
                unit * 0.10,
            )
            path.cubicTo(
                unit * 0.66,
                unit * 0.10,
                unit * 0.78,
                unit * 0.20,
                unit * 0.78,
                unit * 0.40,
            )
            path.cubicTo(
                unit * 0.78,
                unit * 0.58,
                unit * 0.57,
                unit * 0.78,
                unit * 0.50,
                unit * 0.90,
            )
            painter.drawPath(path)
            painter.drawEllipse(
                QRectF(unit * 0.39, unit * 0.29, unit * 0.22, unit * 0.22)
            )
        elif kind == "phone":
            path = QPainterPath()
            path.moveTo(unit * 0.25, unit * 0.13)
            path.cubicTo(
                unit * 0.13,
                unit * 0.20,
                unit * 0.21,
                unit * 0.49,
                unit * 0.36,
                unit * 0.66,
            )
            path.cubicTo(
                unit * 0.51,
                unit * 0.83,
                unit * 0.80,
                unit * 0.91,
                unit * 0.87,
                unit * 0.79,
            )
            path.lineTo(unit * 0.69, unit * 0.61)
            path.cubicTo(
                unit * 0.62,
                unit * 0.68,
                unit * 0.53,
                unit * 0.63,
                unit * 0.45,
                unit * 0.55,
            )
            path.cubicTo(
                unit * 0.37,
                unit * 0.47,
                unit * 0.32,
                unit * 0.38,
                unit * 0.39,
                unit * 0.31,
            )
            path.closeSubpath()
            painter.drawPath(path)
        elif kind == "email":
            envelope = QRectF(unit * 0.12, unit * 0.23, unit * 0.76, unit * 0.56)
            painter.drawRoundedRect(envelope, unit * 0.06, unit * 0.06)
            painter.drawLine(
                QLineF(unit * 0.15, unit * 0.29, unit * 0.50, unit * 0.55)
            )
            painter.drawLine(
                QLineF(unit * 0.85, unit * 0.29, unit * 0.50, unit * 0.55)
            )
        elif kind == "website":
            globe = QRectF(unit * 0.12, unit * 0.12, unit * 0.76, unit * 0.76)
            painter.drawEllipse(globe)
            painter.drawEllipse(
                QRectF(unit * 0.34, unit * 0.12, unit * 0.32, unit * 0.76)
            )
            painter.drawLine(
                QLineF(unit * 0.13, unit * 0.38, unit * 0.87, unit * 0.38)
            )
            painter.drawLine(
                QLineF(unit * 0.13, unit * 0.62, unit * 0.87, unit * 0.62)
            )
        else:
            painter.drawArc(
                QRectF(unit * 0.16, unit * 0.14, unit * 0.68, unit * 0.68),
                0,
                180 * 16,
            )
            painter.drawRoundedRect(
                QRectF(unit * 0.13, unit * 0.45, unit * 0.17, unit * 0.31),
                unit * 0.05,
                unit * 0.05,
            )
            painter.drawRoundedRect(
                QRectF(unit * 0.70, unit * 0.45, unit * 0.17, unit * 0.31),
                unit * 0.05,
                unit * 0.05,
            )
            painter.drawLine(
                QLineF(unit * 0.78, unit * 0.76, unit * 0.66, unit * 0.86)
            )
            painter.drawLine(
                QLineF(unit * 0.66, unit * 0.86, unit * 0.56, unit * 0.86)
            )

        painter.end()
        return pixmap

    def _divider(self, *, vertical: bool = False) -> QFrame:
        divider = QFrame(self.card if hasattr(self, "card") else self)
        divider.setObjectName("sectionDivider")
        divider.setFrameShape(QFrame.Shape.NoFrame)
        thickness = int(THEME.control_stroke_width)
        if vertical:
            divider.setFixedWidth(thickness)
        else:
            divider.setFixedHeight(thickness)
        return divider

    @staticmethod
    def _set_muted(label: QLabel) -> None:
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setOpenExternalLinks(False)
        label.setStyleSheet(f"color: {THEME.text_muted};")
        label.setText("Chưa cập nhật")

    def _set_plain_text(self, label: QLabel, value: str) -> None:
        normalized = value.strip()
        if not normalized:
            self._set_muted(label)
            return
        label.setStyleSheet("")
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setOpenExternalLinks(False)
        label.setText(normalized)

    def _set_link(self, label: QLabel, value: str, kind: str) -> None:
        normalized = value.strip()
        if not normalized:
            self._set_muted(label)
            return
        if kind == "tel":
            destination = f"tel:{quote(normalized, safe='+')}"
        elif kind == "mailto":
            destination = f"mailto:{quote(normalized, safe='@.+')}"
        else:
            destination = (
                normalized
                if normalized.startswith(("http://", "https://"))
                else f"https://{normalized}"
            )
        label.setStyleSheet("")
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setOpenExternalLinks(True)
        label.setText(
            f'<a href="{html.escape(destination, quote=True)}" '
            f'style="color: {THEME.accent}; text-decoration: none;">'
            f"{html.escape(normalized)}</a>"
        )
