"""Built-in transcript correction providers."""

from voicenote.providers.correction.openai import (
    OpenAICorrectionConfig,
    OpenAICorrectionProvider,
)

__all__ = ["OpenAICorrectionConfig", "OpenAICorrectionProvider"]

