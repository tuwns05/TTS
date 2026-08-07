"""TTS contracts, concrete adapters and engine construction."""

from vntts.engines.base import BaseTTSEngine, EngineCapabilities
from vntts.engines.factory import EngineFactory, EngineLifecycleManager, EngineRegistry
from vntts.engines.fake_engine import FakeTTSEngine
from vntts.engines.kokoro_engine import KokoroVIEngine
from vntts.engines.vieneu_engine import VieNeuV2Engine, VieNeuV3Engine

__all__ = [
    "BaseTTSEngine",
    "EngineCapabilities",
    "EngineFactory",
    "EngineLifecycleManager",
    "EngineRegistry",
    "FakeTTSEngine",
    "KokoroVIEngine",
    "VieNeuV2Engine",
    "VieNeuV3Engine",
]
