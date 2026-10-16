from __future__ import annotations

import pytest

from voicenote.config import VoiceNoteConfig


def test_environment_does_not_infer_cloud_consent_from_api_key() -> None:
    config = VoiceNoteConfig.from_env(
        {
            "OPENAI_API_KEY": "secret-not-read-by-config",
            "VOICENOTE_TRANSCRIPTION_PROVIDER": "openai",
        }
    )

    assert config.transcription_provider == "openai"
    assert config.allow_cloud_processing is False


def test_environment_parses_explicit_consent_flags() -> None:
    config = VoiceNoteConfig.from_env(
        {
            "VOICENOTE_ALLOW_CLOUD_PROCESSING": "yes",
            "VOICENOTE_ALLOW_MODEL_DOWNLOAD": "1",
        }
    )

    assert config.allow_cloud_processing is True
    assert config.allow_model_download is True


def test_invalid_environment_boolean_is_rejected() -> None:
    with pytest.raises(ValueError, match="VOICENOTE_ALLOW_CLOUD_PROCESSING"):
        VoiceNoteConfig.from_env({"VOICENOTE_ALLOW_CLOUD_PROCESSING": "sometimes"})

