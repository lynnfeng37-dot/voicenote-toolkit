"""Local-only prerequisite checks shared by built-in cloud adapters."""

import os
from importlib.util import find_spec

from voicenote.exceptions import (
    CloudProcessingDisabledError,
    OptionalDependencyError,
    ProviderNotConfiguredError,
)


def validate_openai_configuration(
    *, allow_cloud_processing: bool, has_client: bool, operation: str
) -> None:
    if not allow_cloud_processing:
        raise CloudProcessingDisabledError(
            f"OpenAI {operation} is disabled; set allow_cloud_processing explicitly"
        )
    if has_client:
        return
    if find_spec("openai") is None:
        raise OptionalDependencyError(
            "OpenAI providers require `pip install voicenote-toolkit[openai]`"
        )
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise ProviderNotConfiguredError("Set OPENAI_API_KEY before using OpenAI providers")
