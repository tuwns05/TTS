"""Runtime capabilities shared by every TTS engine adapter."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EngineCapabilities:
    """Features and devices supported by an engine adapter."""

    voice_cloning: bool
    native_speed_control: bool
    native_pitch_control: bool
    streaming: bool
    cpu_supported: bool
    gpu_supported: bool

