"""Project-specific exceptions with actionable failure boundaries."""


class VoiceNoteError(Exception):
    """Base class for expected VoiceNote failures."""


class InvalidAudioError(VoiceNoteError):
    """Raised when an audio source cannot be validated."""


class ProviderNotConfiguredError(VoiceNoteError):
    """Raised when a requested stage has no configured provider."""


class ProviderError(VoiceNoteError):
    """Raised when a provider fails without a more specific domain error."""


class OptionalDependencyError(ProviderError):
    """Raised when a selected provider's optional package is not installed."""


class CloudProcessingDisabledError(ProviderError):
    """Raised before a cloud provider call when cloud processing is not authorized."""


class CorrectionConflictError(VoiceNoteError):
    """Raised when correction proposals overlap or no longer match their source."""


class ProvenanceError(VoiceNoteError):
    """Raised when a generated artifact cites missing or unsupported source segments."""


class SkillNotFoundError(VoiceNoteError):
    """Raised when a requested domain skill is unavailable."""

