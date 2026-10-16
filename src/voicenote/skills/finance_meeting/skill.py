"""Finance Meeting domain organization built on source-linked Semantic IR."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from voicenote.core.schemas import (
    BriefItem,
    ExecutiveBrief,
    MeetingMinutes,
    NoteSection,
    SemanticDocument,
)
from voicenote.exceptions import ProvenanceError
from voicenote.providers.base import ReasoningProvider, ReasoningRequest
from voicenote.skills.base import VoiceNoteSkill
from voicenote.skills.finance_meeting import manifest


class GeneratedMinutesSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None
    paragraphs: list[str]
    bullets: list[str]
    source_segment_ids: list[str]


class GeneratedFinanceMinutes(BaseModel):
    model_config = ConfigDict(extra="forbid")
    meeting_type: str
    title: str | None
    sections: list[GeneratedMinutesSection]
    warnings: list[str]


class GeneratedBriefItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str
    source_segment_ids: list[str]


class GeneratedExecutiveBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")
    what_happened: list[GeneratedBriefItem]
    important_views: list[GeneratedBriefItem]
    changes: list[GeneratedBriefItem]
    decisions: list[GeneratedBriefItem]
    risks: list[GeneratedBriefItem]
    actions: list[GeneratedBriefItem]


class FinanceMeetingSkill(VoiceNoteSkill):
    """Organize finance content without forcing a universal meeting template."""

    manifest = manifest()

    def organize(
        self, document: SemanticDocument, provider: ReasoningProvider
    ) -> MeetingMinutes:
        generated = provider.generate_structured(
            self._minutes_request(document), GeneratedFinanceMinutes
        )
        meeting_type = (
            generated.meeting_type
            if generated.meeting_type in self.manifest.meeting_types
            else "unknown_finance"
        )
        minutes = MeetingMinutes(
            skill=self.manifest.name,
            meeting_type=meeting_type,
            title=generated.title,
            sections=tuple(
                NoteSection(
                    title=section.title,
                    paragraphs=tuple(section.paragraphs),
                    bullets=tuple(section.bullets),
                    source_segment_ids=tuple(section.source_segment_ids),
                )
                for section in generated.sections
                if section.paragraphs or section.bullets
            ),
            warnings=tuple(generated.warnings) + self._local_warnings(document),
        )
        _validate_minutes(minutes, document)
        return minutes

    def create_brief(
        self,
        minutes: MeetingMinutes,
        document: SemanticDocument,
        provider: ReasoningProvider,
    ) -> ExecutiveBrief:
        generated = provider.generate_structured(
            ReasoningRequest(
                task="create_finance_executive_brief",
                instructions=(
                    "Compress the finance minutes into only material points. Use only supplied "
                    "content; do not add implications or strengthen uncertainty. Put each point "
                    "under the best matching category and preserve its supporting source IDs. "
                    "Omit categories with no supported content."
                ),
                payload={
                    "minutes": minutes.model_dump(mode="json"),
                    "semantic_document": document.model_dump(mode="json"),
                },
            ),
            GeneratedExecutiveBrief,
        )
        brief = ExecutiveBrief(
            what_happened=_brief_items(generated.what_happened),
            important_views=_brief_items(generated.important_views),
            changes=_brief_items(generated.changes),
            decisions=_brief_items(generated.decisions),
            risks=_brief_items(generated.risks),
            actions=_brief_items(generated.actions),
        )
        _validate_brief(brief, document)
        return brief

    def _minutes_request(self, document: SemanticDocument) -> ReasoningRequest:
        return ReasoningRequest(
            task="create_finance_meeting_minutes",
            instructions=(
                "Classify the finance meeting, then choose a content-appropriate structure. "
                "Use only the supplied Semantic IR. Separate facts, attributed views, and open "
                "questions; preserve numbers, periods, units, currencies, qualifications, and "
                "speaker attribution. Do not manufacture headings or content. Omit empty sections. "
                "Every non-empty section must cite source IDs present in its semantic items."
            ),
            payload=document.model_dump(mode="json"),
            references=self._references(),
        )

    def _references(self) -> tuple[str, ...]:
        root = Path(__file__).parent
        references: list[str] = []
        for relative in self.manifest.reference_files:
            path = (root / relative).resolve()
            if path.suffix == ".md" and path.is_relative_to(root.resolve()):
                references.append(path.read_text(encoding="utf-8"))
        return tuple(references)

    @staticmethod
    def _local_warnings(document: SemanticDocument) -> tuple[str, ...]:
        warnings = []
        if document.meeting_type is None:
            warnings.append("Meeting type was not established during semantic extraction.")
        low_confidence = sum(
            item.confidence < 0.8
            for item in (*document.items, *document.entities, *document.open_questions)
        )
        if low_confidence:
            warnings.append(f"{low_confidence} semantic item(s) have confidence below 0.80.")
        return tuple(warnings)


def _brief_items(items: list[GeneratedBriefItem]) -> tuple[BriefItem, ...]:
    return tuple(
        BriefItem(text=item.text, source_segment_ids=tuple(item.source_segment_ids))
        for item in items
    )


def _supported_source_ids(document: SemanticDocument) -> set[str]:
    return {
        source_id
        for item in (*document.items, *document.entities, *document.open_questions)
        for source_id in item.source_segment_ids
    }


def _validate_minutes(minutes: MeetingMinutes, document: SemanticDocument) -> None:
    supported = _supported_source_ids(document)
    for section in minutes.sections:
        if not section.source_segment_ids:
            raise ProvenanceError("Every non-empty minutes section must cite source segments")
        unknown = set(section.source_segment_ids) - supported
        if unknown:
            raise ProvenanceError(f"Unsupported minutes source segments: {sorted(unknown)}")


def _validate_brief(brief: ExecutiveBrief, document: SemanticDocument) -> None:
    supported = _supported_source_ids(document)
    groups = (
        brief.what_happened,
        brief.important_views,
        brief.changes,
        brief.decisions,
        brief.risks,
        brief.actions,
    )
    for item in (item for group in groups for item in group):
        if not item.source_segment_ids:
            raise ProvenanceError("Every executive brief point must cite source segments")
        unknown = set(item.source_segment_ids) - supported
        if unknown:
            raise ProvenanceError(f"Unsupported brief source segments: {sorted(unknown)}")
