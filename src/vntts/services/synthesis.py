"""Synthesize speech through an engine-neutral workflow."""

from __future__ import annotations

import time

from loguru import logger

from vntts.db.models import SynthesisRequest, SynthesisResult, VoiceInfo
from vntts.engines.factory import EngineFactory, EngineLifecycleManager, EngineRegistry
from vntts.utils.exceptions import AppError, EngineLoadError, SynthesisError, ValidationError


class SynthesizeSpeech:
    """Validate a request, prepare an engine and return synthesized audio."""

    def __init__(
        self,
        factory: EngineFactory,
        registry: EngineRegistry,
        max_text_length: int,
        device: str = "auto",
        lifecycle: EngineLifecycleManager | None = None,
    ) -> None:
        self._factory = factory
        self._registry = registry
        self._max_text_length = max_text_length
        self._device = device
        self._lifecycle = lifecycle or EngineLifecycleManager(factory)

    def prepare_engine(self, engine_id: str) -> list[VoiceInfo]:
        """Create and load an engine if needed, then return its voices."""

        if not self._registry.contains(engine_id):
            self._factory.create(engine_id)
        engine = self._lifecycle.get(engine_id)
        if not engine.is_loaded() or self._lifecycle.active_engine_id != engine_id:
            logger.info("Bắt đầu load engine", engine_id=engine_id)
            try:
                engine = self._lifecycle.activate(engine_id, self._device)
            except AppError:
                raise
            except Exception as exc:
                logger.exception("Load engine thất bại", engine_id=engine_id)
                raise EngineLoadError(f"Không thể tải engine '{engine_id}'.") from exc
            logger.info("Load engine thành công", engine_id=engine_id)
        return engine.list_voices()

    def execute(self, request: SynthesisRequest) -> SynthesisResult:
        """Run synthesis without logging the user's text payload."""

        text = request.text.strip()
        if not text:
            raise ValidationError("Văn bản không được để trống.")
        if len(text) > self._max_text_length:
            raise ValidationError(
                f"Văn bản vượt quá giới hạn {self._max_text_length} ký tự."
            )
        if not self._registry.contains(request.engine_id):
            self._factory.create(request.engine_id)

        voices = self.prepare_engine(request.engine_id)
        if request.options.voice_id not in {voice.voice_id for voice in voices}:
            raise ValidationError("Giọng đọc không tồn tại trong engine đã chọn.")

        # TODO(Giai đoạn 4): áp dụng AudioEffects đúng một lần trong AudioProcessor.
        started_at = time.perf_counter()
        logger.info(
            "Bắt đầu tổng hợp",
            engine_id=request.engine_id,
            text_length=len(text),
        )
        try:
            result = self._lifecycle.run_with_active(
                request.engine_id,
                lambda engine: engine.synthesize(text, request.options),
            )
        except AppError:
            raise
        except Exception as exc:
            logger.exception("Tổng hợp thất bại", engine_id=request.engine_id)
            raise SynthesisError("Không thể tổng hợp giọng nói.") from exc
        logger.info(
            "Tổng hợp hoàn tất",
            engine_id=request.engine_id,
            duration_seconds=round(time.perf_counter() - started_at, 3),
        )
        return result

    def unload_all(self) -> None:
        """Release every cached engine adapter during shutdown."""

        self._lifecycle.unload_all()
