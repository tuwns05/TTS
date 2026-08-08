"""Application-level exceptions exposed across architectural boundaries."""


class AppError(Exception):
    """Base class for expected application errors."""


class ConfigurationError(AppError):
    """Raised when application configuration is invalid."""


class EngineNotFoundError(AppError):
    """Raised when an engine identifier is not registered."""


class EngineLoadError(AppError):
    """Raised when a TTS engine cannot be loaded."""


class EngineNotLoadedError(AppError):
    """Raised when synthesis is requested before loading an engine."""


class SynthesisError(AppError):
    """Raised when speech synthesis fails."""


class PlaybackError(AppError):
    """Raised when synthesized audio cannot be prepared or played."""


class DocumentImportError(AppError):
    """Raised when a supported document cannot be converted to plain text."""


class ValidationError(AppError):
    """Raised when user or domain input is invalid."""


class HardwareDetectionError(AppError):
    """Raised when essential hardware information cannot be collected."""
