"""Factory boundary for creating engine adapters by ID."""

from vntts.application.services.engine_registry import EngineRegistry
from vntts.domain.tts.engine import BaseTTSEngine


class EngineFactory:
    """Create engines through a registry without selecting or loading them."""

    def __init__(self, registry: EngineRegistry) -> None:
        self._registry = registry

    def create(self, engine_id: str) -> BaseTTSEngine:
        """Create an engine adapter registered under ``engine_id``."""

        return self._registry.create(engine_id)

