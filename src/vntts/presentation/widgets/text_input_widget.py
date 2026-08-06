"""Text input with a live character count."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPlainTextEdit, QVBoxLayout, QWidget


class TextInputWidget(QWidget):
    """Collect Vietnamese text and display its current length."""

    text_changed = Signal(str)

    def __init__(self, max_length: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._max_length = max_length
        self.editor = QPlainTextEdit(self)
        self.editor.setObjectName("textInput")
        self.editor.setPlaceholderText("Nhập văn bản tiếng Việt cần tổng hợp...")
        self.character_count = QLabel(self)
        self.character_count.setObjectName("characterCount")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Văn bản", self))
        layout.addWidget(self.editor)
        layout.addWidget(self.character_count)
        self.editor.textChanged.connect(self._on_text_changed)
        self._on_text_changed()

    def text(self) -> str:
        """Return the current plain text."""

        return self.editor.toPlainText()

    def _on_text_changed(self) -> None:
        value = self.text()
        self.character_count.setText(f"{len(value)} / {self._max_length} ký tự")
        self.text_changed.emit(value)

