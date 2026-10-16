from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from voicenote.core.schemas import RawTranscript, TerminologyEntry, TranscriptSegment
from voicenote.exceptions import (
    CloudProcessingDisabledError,
    CorrectionConflictError,
    ProviderError,
)
from voicenote.providers.base import CorrectionContext
from voicenote.providers.correction.openai import (
    CorrectionBatch,
    CorrectionCandidate,
    OpenAICorrectionConfig,
    OpenAICorrectionProvider,
)


class FakeResponses:
    def __init__(self, parsed: CorrectionBatch | None) -> None:
        self.parsed = parsed
        self.requests: list[dict[str, Any]] = []

    def parse(self, **kwargs: Any) -> Any:
        self.requests.append(kwargs)
        return SimpleNamespace(output_parsed=self.parsed)


class FakeClient:
    def __init__(self, parsed: CorrectionBatch | None) -> None:
        self.responses = FakeResponses(parsed)


def _candidate(**updates: Any) -> CorrectionCandidate:
    values: dict[str, Any] = {
        "segment_id": "seg-1",
        "original": "夏普币率",
        "corrected": "夏普比率",
        "occurrence_index": 0,
        "confidence": 0.97,
        "reason": "Finance terminology and context",
        "category": "financial_metric",
        "evidence": ["local context"],
        "sensitive": False,
    }
    values.update(updates)
    return CorrectionCandidate.model_validate(values)


def test_correction_requires_explicit_cloud_consent(raw_transcript: RawTranscript) -> None:
    provider = OpenAICorrectionProvider(client=FakeClient(CorrectionBatch(corrections=[])))

    with pytest.raises(CloudProcessingDisabledError):
        provider.propose(raw_transcript, CorrectionContext())


def test_candidate_is_anchored_locally_and_escalated_as_sensitive(
    raw_transcript: RawTranscript,
) -> None:
    client = FakeClient(CorrectionBatch(corrections=[_candidate()]))
    provider = OpenAICorrectionProvider(
        OpenAICorrectionConfig(allow_cloud_processing=True),
        client=client,
    )
    context = CorrectionContext(
        terminology=(
            TerminologyEntry(
                canonical="夏普比率",
                variants=("夏普币率",),
                category="financial_metric",
                sensitive=True,
            ),
        )
    )

    proposals = provider.propose(raw_transcript, context)

    assert proposals[0].span.start == 4
    assert proposals[0].span.end == 8
    assert proposals[0].sensitive is True
    assert "terminology:夏普比率" in proposals[0].evidence
    request = client.responses.requests[0]
    assert request["text_format"] is CorrectionBatch
    assert "夏普币率" in request["input"][1]["content"]


def test_repeated_text_uses_occurrence_index(raw_transcript: RawTranscript) -> None:
    repeated = raw_transcript.model_copy(
        update={
            "segments": (
                raw_transcript.segments[0].model_copy(
                    update={"text": "夏普币率,然后再次说夏普币率"}
                ),
            )
        }
    )
    provider = OpenAICorrectionProvider(
        OpenAICorrectionConfig(allow_cloud_processing=True),
        client=FakeClient(
            CorrectionBatch(corrections=[_candidate(occurrence_index=1, confidence=0.99)])
        ),
    )

    proposals = provider.propose(repeated, CorrectionContext())

    assert proposals[0].span.start == repeated.segments[0].text.rfind("夏普币率")


def test_unanchorable_candidate_fails_closed(raw_transcript: RawTranscript) -> None:
    provider = OpenAICorrectionProvider(
        OpenAICorrectionConfig(allow_cloud_processing=True),
        client=FakeClient(CorrectionBatch(corrections=[_candidate(occurrence_index=4)])),
    )

    with pytest.raises(CorrectionConflictError, match="Could not anchor"):
        provider.propose(raw_transcript, CorrectionContext())


def test_missing_structured_output_is_rejected(raw_transcript: RawTranscript) -> None:
    provider = OpenAICorrectionProvider(
        OpenAICorrectionConfig(allow_cloud_processing=True),
        client=FakeClient(None),
    )

    with pytest.raises(ProviderError, match="no parsed output"):
        provider.propose(raw_transcript, CorrectionContext())


def test_long_transcript_is_split_on_segment_boundaries(raw_transcript: RawTranscript) -> None:
    transcript = raw_transcript.model_copy(
        update={
            "segments": (
                TranscriptSegment(id="seg-a", text="1234"),
                TranscriptSegment(id="seg-b", text="5678"),
            )
        }
    )
    client = FakeClient(CorrectionBatch(corrections=[]))
    provider = OpenAICorrectionProvider(
        OpenAICorrectionConfig(
            allow_cloud_processing=True,
            max_batch_characters=4,
        ),
        client=client,
    )

    assert provider.propose(transcript, CorrectionContext()) == ()
    assert len(client.responses.requests) == 2
    assert "seg-a" in client.responses.requests[0]["input"][1]["content"]
    assert "seg-b" in client.responses.requests[1]["input"][1]["content"]

