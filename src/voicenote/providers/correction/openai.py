"""OpenAI structured-output correction proposals with deterministic anchoring."""

from __future__ import annotations

import json
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from voicenote.core.schemas import (
    CorrectionProposal,
    RawTranscript,
    TerminologyEntry,
    TextSpan,
    TranscriptSegment,
)
from voicenote.core.sensitivity import is_sensitive_correction
from voicenote.exceptions import (
    CloudProcessingDisabledError,
    CorrectionConflictError,
    OptionalDependencyError,
    ProviderError,
)
from voicenote.providers.base import CorrectionContext, CorrectionProvider


class CorrectionCandidate(BaseModel):
    """Model output without trusted character positions."""

    model_config = ConfigDict(extra="forbid")

    segment_id: str
    original: str
    corrected: str
    occurrence_index: int
    confidence: float = Field(ge=0, le=1)
    reason: str
    category: str
    evidence: list[str]
    sensitive: bool


class CorrectionBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    corrections: list[CorrectionCandidate]


class _ResponsesResource(Protocol):
    def parse(self, **kwargs: Any) -> Any: ...


class OpenAICorrectionClientLike(Protocol):
    responses: _ResponsesResource


class OpenAICorrectionConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    model: str = "gpt-4o-mini"
    allow_cloud_processing: bool = False
    max_batch_characters: int = Field(default=12_000, gt=0)


class OpenAICorrectionProvider(CorrectionProvider):
    """Ask for candidate edits, then anchor and validate them locally."""

    name = "openai"

    def __init__(
        self,
        config: OpenAICorrectionConfig | None = None,
        *,
        client: OpenAICorrectionClientLike | None = None,
    ) -> None:
        self.config = config or OpenAICorrectionConfig()
        self._client = client

    def propose(
        self,
        transcript: RawTranscript,
        context: CorrectionContext,
    ) -> tuple[CorrectionProposal, ...]:
        if not self.config.allow_cloud_processing:
            raise CloudProcessingDisabledError(
                "OpenAI correction is disabled; set allow_cloud_processing explicitly"
            )
        candidates: list[CorrectionCandidate] = []
        try:
            for segments in _segment_batches(
                transcript.segments,
                self.config.max_batch_characters,
            ):
                response = self._get_client().responses.parse(
                    model=self.config.model,
                    input=[
                        {"role": "system", "content": _SYSTEM_INSTRUCTIONS},
                        {
                            "role": "user",
                            "content": _request_payload(segments, context),
                        },
                    ],
                    text_format=CorrectionBatch,
                )
                parsed = getattr(response, "output_parsed", None)
                if parsed is None:
                    raise ProviderError(
                        "OpenAI correction returned no parsed output or refused the request"
                    )
                batch = (
                    parsed
                    if isinstance(parsed, CorrectionBatch)
                    else CorrectionBatch.model_validate(parsed)
                )
                candidates.extend(batch.corrections)
        except (CloudProcessingDisabledError, OptionalDependencyError):
            raise
        except ProviderError:
            raise
        except Exception as error:
            raise ProviderError(f"OpenAI correction failed: {error}") from error

        return _anchor_candidates(
            transcript,
            CorrectionBatch(corrections=candidates),
            context,
        )

    def _get_client(self) -> OpenAICorrectionClientLike:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI  # type: ignore[import-not-found]
        except ImportError as error:
            raise OptionalDependencyError(
                "OpenAI correction requires `pip install voicenote-toolkit[openai]`"
            ) from error
        self._client = OpenAI()
        return self._client


_SYSTEM_INSTRUCTIONS = """You identify likely ASR recognition errors without rewriting speech.
Return only corrections supported by local context or supplied terminology. Preserve meaning,
filler words, repetitions, tone, and language switching. Do not improve style or summarize.
For each candidate, copy the exact original substring from one segment. occurrence_index is the
zero-based occurrence of that exact substring within the segment. Use calibrated confidence.
Treat numbers, dates, percentages, names, companies, tickers, valuation multiples, and financial
metrics as sensitive. When evidence is weak, omit the correction rather than guessing."""


def _request_payload(
    segments: tuple[TranscriptSegment, ...],
    context: CorrectionContext,
) -> str:
    payload = {
        "segments": [
            {
                "id": item.id,
                "text": item.text,
                "speaker": item.speaker,
                "language": item.language,
                "start_seconds": item.start_seconds,
                "end_seconds": item.end_seconds,
            }
            for item in segments
        ],
        "terminology": [entry.model_dump(mode="json") for entry in context.terminology],
        "language_hints": list(context.language_hints),
        "sensitive_categories": list(context.sensitive_categories),
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _segment_batches(
    segments: tuple[TranscriptSegment, ...],
    max_characters: int,
) -> tuple[tuple[TranscriptSegment, ...], ...]:
    batches: list[tuple[TranscriptSegment, ...]] = []
    current: list[TranscriptSegment] = []
    current_size = 0
    for segment in segments:
        segment_size = len(segment.text)
        if current and current_size + segment_size > max_characters:
            batches.append(tuple(current))
            current = []
            current_size = 0
        current.append(segment)
        current_size += segment_size
    if current:
        batches.append(tuple(current))
    return tuple(batches)


def _anchor_candidates(
    transcript: RawTranscript,
    batch: CorrectionBatch,
    context: CorrectionContext,
) -> tuple[CorrectionProposal, ...]:
    segments = {segment.id: segment.text for segment in transcript.segments}
    proposals: list[CorrectionProposal] = []
    for candidate in batch.corrections:
        if candidate.segment_id not in segments:
            raise CorrectionConflictError(f"Unknown segment id: {candidate.segment_id}")
        if candidate.original == candidate.corrected:
            continue
        start = _occurrence_start(
            segments[candidate.segment_id],
            candidate.original,
            candidate.occurrence_index,
        )
        terminology_evidence, term_sensitive = _terminology_match(candidate, context.terminology)
        sensitive = (
            candidate.sensitive
            or term_sensitive
            or is_sensitive_correction(
                candidate.original,
                candidate.corrected,
                candidate.category,
                context.sensitive_categories,
            )
        )
        evidence = tuple(dict.fromkeys([*candidate.evidence, *terminology_evidence]))
        proposals.append(
            CorrectionProposal(
                segment_id=candidate.segment_id,
                original=candidate.original,
                corrected=candidate.corrected,
                span=TextSpan(start=start, end=start + len(candidate.original)),
                confidence=candidate.confidence,
                reason=candidate.reason,
                category=candidate.category,
                evidence=evidence,
                sensitive=sensitive,
            )
        )
    return tuple(proposals)


def _occurrence_start(text: str, original: str, occurrence_index: int) -> int:
    if not original:
        raise CorrectionConflictError("Correction original text cannot be empty")
    if occurrence_index < 0:
        raise CorrectionConflictError("Correction occurrence_index cannot be negative")
    positions: list[int] = []
    offset = 0
    while True:
        position = text.find(original, offset)
        if position < 0:
            break
        positions.append(position)
        offset = position + max(1, len(original))
    if occurrence_index >= len(positions):
        raise CorrectionConflictError(
            f"Could not anchor occurrence {occurrence_index} of {original!r}"
        )
    return positions[occurrence_index]


def _terminology_match(
    candidate: CorrectionCandidate,
    terminology: tuple[TerminologyEntry, ...],
) -> tuple[list[str], bool]:
    evidence: list[str] = []
    sensitive = False
    for entry in terminology:
        accepted_forms = {entry.canonical, *entry.variants}
        if candidate.original in accepted_forms or candidate.corrected in accepted_forms:
            evidence.append(f"terminology:{entry.canonical}")
            sensitive = sensitive or entry.sensitive
    return evidence, sensitive

