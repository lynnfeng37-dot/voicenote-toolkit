"""Vendor-neutral provider interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict

from voicenote.core.schemas import (
    AudioSource,
    CorrectedTranscript,
    CorrectionProposal,
    RawTranscript,
    TerminologyEntry,
)

StructuredResult = TypeVar("StructuredResult", bound=BaseModel)


class TranscriptionOptions(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    language: str | None = None
    language_hints: tuple[str, ...] = ()
    prompt_terms: tuple[str, ...] = ()
    timestamps: bool = True
    diarization: bool = False


class CorrectionContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    terminology: tuple[TerminologyEntry, ...] = ()
    language_hints: tuple[str, ...] = ()
    sensitive_categories: tuple[str, ...] = (
        "number",
        "percentage",
        "date",
        "company_name",
        "personal_name",
        "ticker_symbol",
        "valuation_multiple",
        "financial_metric",
    )


class ReasoningRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    task: str
    instructions: str
    payload: dict[str, Any]
    references: tuple[str, ...] = ()


class TranscriptionProvider(ABC):
    """Turn local audio metadata into an immutable raw transcript."""

    name: str

    @abstractmethod
    def transcribe(self, audio: AudioSource, options: TranscriptionOptions) -> RawTranscript:
        """Transcribe audio without rewriting the provider's recognized text."""


class CorrectionProvider(ABC):
    """Propose corrections; the deterministic core decides whether to apply them."""

    name: str

    @abstractmethod
    def propose(
        self,
        transcript: RawTranscript,
        context: CorrectionContext,
    ) -> tuple[CorrectionProposal, ...]:
        """Return auditable proposals without mutating the transcript."""


class ReasoningProvider(ABC):
    """Generate schema-constrained semantic artifacts."""

    name: str

    @abstractmethod
    def generate_structured(
        self,
        request: ReasoningRequest,
        response_model: type[StructuredResult],
    ) -> StructuredResult:
        """Return a value validated by response_model."""


class NoOpCorrectionProvider(CorrectionProvider):
    """Useful for transcription-only workflows and deterministic tests."""

    name = "none"

    def propose(
        self,
        transcript: RawTranscript,
        context: CorrectionContext,
    ) -> tuple[CorrectionProposal, ...]:
        del transcript, context
        return ()


def corrected_payload(transcript: CorrectedTranscript) -> dict[str, Any]:
    """Serialize a corrected transcript consistently for reasoning providers."""

    return transcript.model_dump(mode="json")

