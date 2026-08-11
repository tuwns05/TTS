"""Reusable themed controls whose native rendering varies across platforms."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen, QPolygonF
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QListView,
    QProxyStyle,
    QStyle,
    QStyledItemDelegate,
)

from vntts.config.theme import THEME


class _ComboPopupStyle(QProxyStyle):
    def styleHint(self, hint, option=None, widget=None, return_data=None):
        if hint == QStyle.StyleHint.SH_ComboBox_Popup:
            return 0
        return super().styleHint(hint, option, widget, return_data)


class _ComboItemDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index) -> QSize:
        size = super().sizeHint(option, index)
        size.setHeight(max(size.height(), THEME.combo_popup_row_height))
        return size


class ChevronComboBox(QComboBox):
    """Draw a consistent antialiased chevron instead of the OS-native arrow."""

    def __init__(self, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self._popup_open = False
        self._popup_style = _ComboPopupStyle()
        self._popup_style.setParent(self)
        self.setStyle(self._popup_style)
        self.setMaxVisibleItems(THEME.combo_max_visible_items)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        popup = self.view()
        popup.setItemDelegate(_ComboItemDelegate(popup))
        popup.setTextElideMode(Qt.TextElideMode.ElideRight)
        popup.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        popup.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        popup.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        if isinstance(popup, QListView):
            popup.setUniformItemSizes(True)
            popup.setSpacing(THEME.space_1 // 2)

    def showPopup(self) -> None:
        self._popup_open = True
        self.update()
        super().showPopup()

    def hidePopup(self) -> None:
        super().hidePopup()
        self._popup_open = False
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)

        color = THEME.text_secondary if self.isEnabled() else THEME.text_disabled
        center_x = self.width() - THEME.space_4
        center_y = self.height() / 2
        half_width = THEME.combo_arrow_size / 2
        half_height = THEME.combo_arrow_size / 4
        direction = -1 if self._popup_open else 1
        points = QPolygonF(
            [
                QPointF(center_x - half_width, center_y - direction * half_height),
                QPointF(center_x, center_y + direction * half_height),
                QPointF(center_x + half_width, center_y - direction * half_height),
            ]
        )

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(QColor(color), THEME.control_stroke_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolyline(points)
