"""Safe runtime configuration with explicit provider and network choices."""

import os
from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class VoiceNoteConfig(BaseModel):
    """Runtime settings that are safe to serialize into a run manifest."""

    model_config = ConfigDict(frozen=True)

    output_dir: Path = Path("output")
    log_level: str = "INFO"
    keep_temporary_files: bool = False
    allow_cloud_processing: bool = False
    allow_model_download: bool = False
    transcription_provider: str | None = None
    transcription_model: str | None = None
    correction_provider: str | None = None
    correction_model: str | None = None
    reasoning_provider: str | None = None
    reasoning_model: str | None = None
    local_device: str = "auto"
    local_compute_type: str = "default"
    high_confidence_threshold: float = Field(default=0.90, ge=0, le=1)
    medium_confidence_threshold: float = Field(default=0.70, ge=0, le=1)
    sensitive_high_threshold: float = Field(default=0.98, ge=0, le=1)
    sensitive_medium_threshold: float = Field(default=0.92, ge=0, le=1)

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "VoiceNoteConfig":
        """Load non-secret settings without interpreting the presence of API keys as consent."""

        values = os.environ if environ is None else environ
        return cls(
            output_dir=Path(values.get("VOICENOTE_OUTPUT_DIR", "output")),
            log_level=values.get("VOICENOTE_LOG_LEVEL", "INFO"),
            allow_cloud_processing=_env_bool(values, "VOICENOTE_ALLOW_CLOUD_PROCESSING"),
            allow_model_download=_env_bool(values, "VOICENOTE_ALLOW_MODEL_DOWNLOAD"),
            transcription_provider=values.get("VOICENOTE_TRANSCRIPTION_PROVIDER") or None,
            transcription_model=values.get("VOICENOTE_TRANSCRIPTION_MODEL") or None,
            correction_provider=values.get("VOICENOTE_CORRECTION_PROVIDER") or None,
            correction_model=values.get("VOICENOTE_CORRECTION_MODEL") or None,
            reasoning_provider=values.get("VOICENOTE_REASONING_PROVIDER") or None,
            reasoning_model=values.get("VOICENOTE_REASONING_MODEL") or None,
            local_device=values.get("VOICENOTE_LOCAL_DEVICE", "auto"),
            local_compute_type=values.get("VOICENOTE_LOCAL_COMPUTE_TYPE", "default"),
        )


def _env_bool(values: Mapping[str, str], name: str) -> bool:
    value = values.get(name, "").strip().lower()
    if value in {"", "0", "false", "no", "off"}:
        return False
    if value in {"1", "true", "yes", "on"}:
        return True
    raise ValueError(f"{name} must be a boolean value")

