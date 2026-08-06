"""Disabled playback controls reserved for a later phase."""

from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget


class PlaybackControls(QWidget):
    """Show the planned Play/Pause/Stop controls without fake playback."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        for name, label in (("playButton", "Play"), ("pauseButton", "Pause"), ("stopButton", "Stop")):
            button = QPushButton(label, self)
            button.setObjectName(name)
            button.setEnabled(False)
            button.setToolTip("Playback thật sẽ được triển khai ở Giai đoạn 5.")
            layout.addWidget(button)

