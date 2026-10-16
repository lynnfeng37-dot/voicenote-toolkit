"""OpenAI file-transcription adapter with an explicit cloud consent gate."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from voicenote.core.schemas import (
    AudioSource,
    ProviderMetadata,
    RawTranscript,
    TranscriptSegment,
)
from voicenote.exceptions import (
    CloudProcessingDisabledError,
    OptionalDependencyError,
    ProviderError,
)
from voicenote.providers.base import TranscriptionOptions, TranscriptionProvider

OPENAI_MAX_FILE_BYTES = 25 * 1024 * 1024


class _TranscriptionsResource(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


class _AudioResource(Protocol):
    transcriptions: _TranscriptionsResource


class OpenAIClientLike(Protocol):
    audio: _AudioResource


class OpenAITranscriptionConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    model: str = "whisper-1"
    diarization_model: str = "gpt-4o-transcribe-diarize"
    allow_cloud_processing: bool = False
    max_file_bytes: int = Field(default=OPENAI_MAX_FILE_BYTES, gt=0)


class OpenAITranscriptionProvider(TranscriptionProvider):
    """Map OpenAI transcription responses into VoiceNote's immutable raw schema."""

    name = "openai"

    def __init__(
        self,
        config: OpenAITranscriptionConfig | None = None,
        *,
        client: OpenAIClientLike | None = None,
    ) -> None:
        self.config = config or OpenAITranscriptionConfig()
        self._client = client

    def transcribe(self, audio: AudioSource, options: TranscriptionOptions) -> RawTranscript:
        if not self.config.allow_cloud_processing:
            raise CloudProcessingDisabledError(
                "OpenAI transcription is disabled; set allow_cloud_processing explicitly"
            )
        if audio.size_bytes > self.config.max_file_bytes:
            raise ProviderError(
                f"OpenAI transcription input exceeds {self.config.max_file_bytes} bytes; "
                "split or compress it before upload"
            )

        model = self.config.diarization_model if options.diarization else self.config.model
        request = self._build_request(model, options)
        try:
            with Path(audio.path).open("rb") as audio_file:
                response = self._get_client().audio.transcriptions.create(
                    model=model,
                    file=audio_file,
                    **request,
                )
        except (CloudProcessingDisabledError, OptionalDependencyError):
            raise
        except Exception as error:
            raise ProviderError(f"OpenAI transcription failed: {error}") from error

        return _map_response(audio, model, response)

    def _build_request(self, model: str, options: TranscriptionOptions) -> dict[str, Any]:
        request: dict[str, Any] = {}
        if options.diarization:
            request.update(response_format="diarized_json", chunking_strategy="auto")
        elif model == "whisper-1":
            request.update(
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )
        else:
            request["response_format"] = "json"

        if options.language:
            request["language"] = options.language
        if options.prompt_terms and not options.diarization:
            request["prompt"] = ", ".join(options.prompt_terms)
        return request

    def _get_client(self) -> OpenAIClientLike:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI  # type: ignore[import-not-found]
        except ImportError as error:
            raise OptionalDependencyError(
                "OpenAI provider requires `pip install voicenote-toolkit[openai]`"
            ) from error
        self._client = OpenAI()
        return self._client


def _map_response(audio: AudioSource, model: str, response: Any) -> RawTranscript:
    data = _as_mapping(response)
    raw_segments = data.get("segments") or []
    segments: list[TranscriptSegment] = []
    for index, raw_segment in enumerate(raw_segments):
        item = _as_mapping(raw_segment)
        text = str(item.get("text", ""))
        segment_id = str(item.get("id", f"seg-{index:04d}"))
        segments.append(
            TranscriptSegment(
                id=segment_id,
                text=text,
                start_seconds=_optional_float(item.get("start")),
                end_seconds=_optional_float(item.get("end")),
                speaker=_optional_str(item.get("speaker")),
                language=_optional_str(data.get("language")),
                provider_metadata=_segment_metadata(item),
            )
        )

    if not segments:
        segments.append(
            TranscriptSegment(
                id="seg-0000",
                text=str(data.get("text", "")),
                language=_optional_str(data.get("language")),
            )
        )

    language = _optional_str(data.get("language"))
    return RawTranscript(
        audio=audio,
        segments=tuple(segments),
        provider=ProviderMetadata(provider="openai", model=model),
        detected_languages=(language,) if language else (),
    )


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, Mapping):
            return dumped
    raise ProviderError(f"Unexpected transcription response type: {type(value).__name__}")


def _segment_metadata(item: Mapping[str, Any]) -> dict[str, Any]:
    keys = ("avg_logprob", "compression_ratio", "no_speech_prob", "temperature")
    return {key: item[key] for key in keys if item.get(key) is not None}


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)

