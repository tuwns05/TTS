"""TTS engine contracts and models."""

from vntts.domain.tts.capabilities import EngineCapabilities
from vntts.domain.tts.engine import BaseTTSEngine
from vntts.domain.tts.models import (
    AudioEffects,
    EngineInfo,
    EngineSynthesisOptions,
    SynthesisRequest,
    SynthesisResult,
    VoiceInfo,
)

__all__ = [
    "AudioEffects",
    "BaseTTSEngine",
    "EngineCapabilities",
    "EngineInfo",
    "EngineSynthesisOptions",
    "SynthesisRequest",
    "SynthesisResult",
    "VoiceInfo",
]

