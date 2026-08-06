"""Lazy registry of available TTS engine providers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from vntts.domain.exceptions import EngineNotFoundError, ValidationError
from vntts.domain.tts.engine import BaseTTSEngine
from vntts.domain.tts.models import EngineInfo

EngineProvider = Callable[[], BaseTTSEngine]


@dataclass(frozen=True)
class _Registration:
    provider: EngineProvider
    engine_info: EngineInfo


class EngineRegistry:
    """Register providers without loading their model resources."""

    def __init__(self) -> None:
        self._registrations: dict[str, _Registration] = {}

    def register(
        self,
        engine_id: str,
        provider: EngineProvider,
        engine_info: EngineInfo | None = None,
    ) -> None:
        """Register an engine provider under a unique identifier."""

        normalized_id = engine_id.strip()
        if not normalized_id:
            raise ValidationError("Mã engine đăng ký không được để trống.")
        if normalized_id in self._registrations:
            raise ValidationError(f"Engine '{normalized_id}' đã được đăng ký.")
        if not callable(provider):
            raise ValidationError("Engine provider phải là callable.")

        metadata = engine_info
        if metadata is None:
            candidate = provider()
            if not isinstance(candidate, BaseTTSEngine):
                raise ValidationError("Engine provider không trả về BaseTTSEngine.")
            metadata = candidate.engine_info
        if metadata.engine_id != normalized_id:
            raise ValidationError("Engine ID đăng ký không khớp metadata.")
        self._registrations[normalized_id] = _Registration(provider, metadata)

    def contains(self, engine_id: str) -> bool:
        """Return whether an engine identifier is registered."""

        return engine_id in self._registrations

    def create(self, engine_id: str) -> BaseTTSEngine:
        """Create a lightweight engine adapter from its provider."""

        registration = self._registrations.get(engine_id)
        if registration is None:
            raise EngineNotFoundError(f"Không tìm thấy engine '{engine_id}'.")
        engine = registration.provider()
        if not isinstance(engine, BaseTTSEngine):
            raise ValidationError("Engine provider không trả về BaseTTSEngine.")
        if engine.engine_info.engine_id != engine_id:
            raise ValidationError("Engine provider trả về engine có ID không khớp.")
        return engine

    def list_engine_ids(self) -> list[str]:
        """List registered identifiers without invoking providers."""

        return list(self._registrations)

    def list_engine_info(self) -> list[EngineInfo]:
        """List cached engine metadata without creating adapters."""

        return [item.engine_info for item in self._registrations.values()]

