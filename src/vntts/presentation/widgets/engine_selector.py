"""Engine selector and recommendation hint."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QLabel, QVBoxLayout, QWidget

from vntts.domain.hardware.models import EngineRecommendation
from vntts.domain.tts.models import EngineInfo


class EngineSelector(QWidget):
    """Display only registered engines and an optional recommendation."""

    engine_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.combo = QComboBox(self)
        self.combo.setObjectName("engineCombo")
        self.recommendation_label = QLabel(self)
        self.recommendation_label.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Engine", self))
        layout.addWidget(self.combo)
        layout.addWidget(self.recommendation_label)
        self.combo.currentIndexChanged.connect(self._emit_current_engine)

    def set_engines(self, engines: list[EngineInfo], selected_id: str | None = None) -> None:
        """Replace choices using metadata already cached by the registry."""

        self.combo.blockSignals(True)
        self.combo.clear()
        selected_index = 0
        for index, engine in enumerate(engines):
            self.combo.addItem(engine.display_name, engine.engine_id)
            if engine.engine_id == selected_id:
                selected_index = index
        if self.combo.count():
            self.combo.setCurrentIndex(selected_index)
        self.combo.blockSignals(False)

    def set_recommendation(self, recommendation: EngineRecommendation | None) -> None:
        """Show a non-binding recommendation without adding unregistered engines."""

        if recommendation is None:
            self.recommendation_label.clear()
            return
        self.recommendation_label.setText(
            f"Khuyến nghị khi khả dụng: {recommendation.engine_id} — {recommendation.reason}"
        )

    def current_engine_id(self) -> str | None:
        """Return the selected registered engine identifier."""

        value = self.combo.currentData()
        return str(value) if value is not None else None

    def _emit_current_engine(self) -> None:
        engine_id = self.current_engine_id()
        if engine_id is not None:
            self.engine_changed.emit(engine_id)

