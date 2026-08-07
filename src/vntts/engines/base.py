"""Engine-neutral TTS adapter contract."""

from abc import ABC, abstractmethod

from vntts.domain.tts.capabilities import EngineCapabilities
from vntts.domain.tts.models import (
    EngineInfo,
    EngineSynthesisOptions,
    SynthesisResult,
    VoiceInfo,
)


class BaseTTSEngine(ABC):
    """Contract implemented by every concrete TTS engine adapter."""

    @property
    @abstractmethod
    def engine_info(self) -> EngineInfo:
        """Return stable metadata without loading the model."""

    @property
    @abstractmethod
    def capabilities(self) -> EngineCapabilities:
        """Return capabilities available through this adapter."""

    @abstractmethod
    def load(self, device: str) -> None:
        """Load engine resources for the requested device."""

    @abstractmethod
    def unload(self) -> None:
        """Release resources held by the engine."""

    @abstractmethod
    def is_loaded(self) -> bool:
        """Return whether engine resources are ready."""

    @abstractmethod
    def list_voices(self) -> list[VoiceInfo]:
        """List voices exposed by the current engine."""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        options: EngineSynthesisOptions,
    ) -> SynthesisResult:
        """Synthesize text into an engine-neutral audio result."""

