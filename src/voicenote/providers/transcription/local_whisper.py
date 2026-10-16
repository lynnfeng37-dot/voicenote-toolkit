"""Local faster-whisper adapter with lazy model loading."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, Protocol, cast

from pydantic import BaseModel, ConfigDict

from voicenote.core.schemas import (
    AudioSource,
    ProviderMetadata,
    RawTranscript,
    TranscriptSegment,
)
from voicenote.exceptions import OptionalDependencyError, ProviderError
from voicenote.providers.base import TranscriptionOptions, TranscriptionProvider


class WhisperSegmentLike(Protocol):
    id: int
    text: str
    start: float
    end: float
    avg_logprob: float
    compression_ratio: float
    no_speech_prob: float


class WhisperInfoLike(Protocol):
    language: str
    language_probability: float
    duration: float


class WhisperModelLike(Protocol):
    def transcribe(
        self,
        audio: str,
        **kwargs: Any,
    ) -> tuple[Iterable[WhisperSegmentLike], WhisperInfoLike]: ...


ModelFactory = Callable[..., WhisperModelLike]


class LocalWhisperConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    model: str = "small"
    device: str = "auto"
    compute_type: str = "default"
    download_root: Path | None = None
    allow_model_download: bool = False
    vad_filter: bool = True
    beam_size: int = 5


class LocalWhisperProvider(TranscriptionProvider):
    """Run ASR locally; model acquisition is separately consented."""

    name = "local_whisper"

    def __init__(
        self,
        config: LocalWhisperConfig | None = None,
        *,
        model_factory: ModelFactory | None = None,
    ) -> None:
        self.config = config or LocalWhisperConfig()
        self._model_factory = model_factory
        self._model: WhisperModelLike | None = None

    def transcribe(self, audio: AudioSource, options: TranscriptionOptions) -> RawTranscript:
        if options.diarization:
            raise ProviderError("LocalWhisperProvider does not provide speaker diarization")
        prompt = ", ".join(options.prompt_terms) or None
        try:
            segment_stream, info = self._get_model().transcribe(
                audio.path,
                language=options.language,
                initial_prompt=prompt,
                hotwords=prompt,
                beam_size=self.config.beam_size,
                vad_filter=self.config.vad_filter,
                without_timestamps=not options.timestamps,
            )
            raw_segments = list(segment_stream)
        except (OptionalDependencyError, ProviderError):
            raise
        except Exception as error:
            raise ProviderError(f"Local faster-whisper transcription failed: {error}") from error

        language = info.language or options.language
        segments = tuple(
            TranscriptSegment(
                id=f"seg-{segment.id:04d}",
                text=segment.text,
                start_seconds=segment.start if options.timestamps else None,
                end_seconds=segment.end if options.timestamps else None,
                language=language,
                provider_metadata={
                    "avg_logprob": segment.avg_logprob,
                    "compression_ratio": segment.compression_ratio,
                    "no_speech_prob": segment.no_speech_prob,
                },
            )
            for segment in raw_segments
        )
        return RawTranscript(
            audio=audio,
            segments=segments,
            provider=ProviderMetadata(
                provider=self.name,
                model=self.config.model,
                extra={
                    "device": self.config.device,
                    "compute_type": self.config.compute_type,
                    "language_probability": info.language_probability,
                    "duration_seconds": info.duration,
                },
            ),
            detected_languages=(language,) if language else (),
        )

    def _get_model(self) -> WhisperModelLike:
        if self._model is not None:
            return self._model
        factory = self._model_factory or _load_model_factory()
        self._model = factory(
            self.config.model,
            device=self.config.device,
            compute_type=self.config.compute_type,
            download_root=(str(self.config.download_root) if self.config.download_root else None),
            local_files_only=not self.config.allow_model_download,
        )
        return self._model


def _load_model_factory() -> ModelFactory:
    try:
        from faster_whisper import WhisperModel  # type: ignore[import-not-found]
    except ImportError as error:
        raise OptionalDependencyError(
            "Local provider requires `pip install voicenote-toolkit[local-asr]`"
        ) from error
    return cast(ModelFactory, WhisperModel)

