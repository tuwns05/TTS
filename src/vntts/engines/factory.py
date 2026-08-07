"""Registry, factory and lifecycle coordination for TTS engines."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from threading import RLock
from typing import TypeVar

from loguru import logger

from vntts.db.models import EngineInfo
from vntts.engines.base import BaseTTSEngine, EngineCapabilities
from vntts.utils.exceptions import (
    AppError,
    EngineLoadError,
    EngineNotFoundError,
    ValidationError,
)

EngineProvider = Callable[[], BaseTTSEngine]
ResultT = TypeVar("ResultT")


@dataclass(frozen=True)
class _Registration:
    provider: EngineProvider
    engine_info: EngineInfo
    capabilities: EngineCapabilities | None


class EngineRegistry:
    """Register providers without loading their model resources."""

    def __init__(self) -> None:
        self._registrations: dict[str, _Registration] = {}

    def register(
        self,
        engine_id: str,
        provider: EngineProvider,
        engine_info: EngineInfo | None = None,
        capabilities: EngineCapabilities | None = None,
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
        self._registrations[normalized_id] = _Registration(provider, metadata, capabilities)

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

    def get_capabilities(self, engine_id: str) -> EngineCapabilities:
        """Return capabilities without loading model resources."""

        registration = self._registrations.get(engine_id)
        if registration is None:
            raise EngineNotFoundError(f"Không tìm thấy engine '{engine_id}'.")
        if registration.capabilities is not None:
            return registration.capabilities
        return self.create(engine_id).capabilities


class EngineFactory:
    """Create engines through a registry without selecting or loading them."""

    def __init__(self, registry: EngineRegistry) -> None:
        self._registry = registry

    def create(self, engine_id: str) -> BaseTTSEngine:
        """Create an engine adapter registered under ``engine_id``."""

        return self._registry.create(engine_id)


class EngineLifecycleManager:
    """Keep at most one model loaded while reusing lightweight adapters."""

    def __init__(self, factory: EngineFactory) -> None:
        self._factory = factory
        self._engines: dict[str, BaseTTSEngine] = {}
        self._active_engine_id: str | None = None
        self._lock = RLock()

    @property
    def active_engine_id(self) -> str | None:
        """Return the currently loaded engine ID, if any."""

        with self._lock:
            return self._active_engine_id

    def get(self, engine_id: str) -> BaseTTSEngine:
        """Return a cached lightweight adapter, creating it when necessary."""

        with self._lock:
            engine = self._engines.get(engine_id)
            if engine is None:
                engine = self._factory.create(engine_id)
                self._engines[engine_id] = engine
            return engine

    def activate(self, engine_id: str, device: str = "auto") -> BaseTTSEngine:
        """Unload the previous engine, then load and activate the requested one."""

        with self._lock:
            target = self.get(engine_id)
            if self._active_engine_id == engine_id and target.is_loaded():
                return target
            if not target.is_available():
                raise EngineLoadError(
                    f"Engine '{engine_id}' chưa đủ SDK hoặc model local để hoạt động."
                )

            if self._active_engine_id is not None and self._active_engine_id != engine_id:
                self.unload(self._active_engine_id)

            try:
                if not target.is_loaded():
                    target.load(device)
            except AppError:
                self._active_engine_id = None
                raise
            except Exception as exc:
                self._active_engine_id = None
                raise EngineLoadError(f"Không thể tải engine '{engine_id}'.") from exc

            self._active_engine_id = engine_id
            return target

    def run_with_active(
        self,
        engine_id: str,
        operation: Callable[[BaseTTSEngine], ResultT],
    ) -> ResultT:
        """Run an operation while preventing concurrent unload or engine switch."""

        with self._lock:
            engine = self.get(engine_id)
            if self._active_engine_id != engine_id or not engine.is_loaded():
                raise EngineLoadError(f"Engine '{engine_id}' chưa được kích hoạt.")
            return operation(engine)

    def unload(self, engine_id: str) -> None:
        """Release one cached engine and clear its active state."""

        with self._lock:
            engine = self._engines.get(engine_id)
            if engine is None:
                return
            try:
                engine.unload()
            except Exception:
                logger.exception("Không thể unload engine", engine_id=engine_id)
            finally:
                if self._active_engine_id == engine_id:
                    self._active_engine_id = None

    def unload_all(self) -> None:
        """Release all adapters during application shutdown."""

        with self._lock:
            for engine_id in tuple(self._engines):
                self.unload(engine_id)
            self._engines.clear()
