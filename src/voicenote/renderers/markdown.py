"""Human-readable projection of available artifacts."""

from voicenote.core.schemas import (
    BriefItem,
    CleanNotes,
    CorrectionDecision,
    ExecutiveBrief,
    MeetingMinutes,
    NoteSection,
    ReviewConcern,
    VoiceNoteResult,
)
from voicenote.renderers.base import Renderer


class MarkdownRenderer(Renderer):
    def render(self, result: VoiceNoteResult) -> str:
        lines = ["# VoiceNote Result", ""]
        if result.corrected_transcript is not None:
            lines.extend(["## Corrected transcript", "", result.corrected_transcript.text, ""])
        elif result.raw_transcript is not None:
            lines.extend(["## Raw transcript", "", result.raw_transcript.text, ""])

        if result.notes is not None:
            lines.extend(["## Notes", ""])
            lines.extend(_render_sections(result.notes.sections))
            lines.extend(_render_review_concerns(result.notes.review_concerns))
        if result.meeting_minutes is not None:
            lines.extend(["## Meeting minutes", ""])
            lines.extend(_render_sections(result.meeting_minutes.sections))
            lines.extend(_render_review_concerns(result.meeting_minutes.review_concerns))
        if result.executive_brief is not None:
            lines.extend(["## Executive brief", ""])
            lines.extend(_render_brief_groups(result.executive_brief))
            lines.extend(_render_review_concerns(result.executive_brief.review_concerns))
        return "\n".join(lines).rstrip() + "\n"

    def render_notes(self, notes: CleanNotes) -> str:
        lines = [f"# {notes.title or 'Clean Notes'}", ""]
        lines.extend(_render_sections(notes.sections))
        lines.extend(_render_review_concerns(notes.review_concerns))
        return "\n".join(lines).rstrip() + "\n"

    def render_minutes(self, minutes: MeetingMinutes) -> str:
        lines = [f"# {minutes.title or 'Finance Meeting Minutes'}", ""]
        lines.extend([f"Meeting type: `{minutes.meeting_type}`", ""])
        lines.extend(_render_sections(minutes.sections))
        lines.extend(_render_review_concerns(minutes.review_concerns))
        if minutes.warnings:
            lines.extend(["## Warnings", ""])
            lines.extend(f"- {warning}" for warning in minutes.warnings)
        return "\n".join(lines).rstrip() + "\n"

    def render_brief(self, brief: ExecutiveBrief) -> str:
        lines = ["# Executive Brief", ""]
        lines.extend(_render_brief_groups(brief))
        lines.extend(_render_review_concerns(brief.review_concerns))
        return "\n".join(lines).rstrip() + "\n"


def _render_sections(sections: tuple[NoteSection, ...]) -> list[str]:
    lines: list[str] = []
    for section in sections:
        if section.title:
            lines.extend([f"### {section.title}", ""])
        for paragraph in section.paragraphs:
            lines.extend([paragraph, ""])
        for bullet in section.bullets:
            lines.append(f"- {bullet}")
        if section.bullets:
            lines.append("")
        if section.source_segment_ids:
            lines.extend([f"*Sources: {', '.join(section.source_segment_ids)}*", ""])
        if section.review_concerns:
            lines.extend(["> Review required: this section cites a flagged source segment.", ""])
    return lines


def _render_brief_groups(brief: ExecutiveBrief) -> list[str]:
    groups = (
        ("What happened", brief.what_happened),
        ("Important views", brief.important_views),
        ("Changes", brief.changes),
        ("Decisions", brief.decisions),
        ("Risks", brief.risks),
        ("Actions", brief.actions),
    )
    lines: list[str] = []
    for title, items in groups:
        if not items:
            continue
        lines.extend([f"### {title}", ""])
        lines.extend(_render_brief_items(items))
    return lines


def _render_brief_items(items: tuple[BriefItem, ...]) -> list[str]:
    return [
        f"- {item.text} *(Sources: {', '.join(item.source_segment_ids)})*"
        + (" **[Review required]**" if item.review_concerns else "")
        for item in items
    ] + [""]


def _render_review_concerns(concerns: tuple[ReviewConcern, ...]) -> list[str]:
    if not concerns:
        return []
    lines = ["### Source corrections requiring review", ""]
    for concern in concerns:
        status = (
            "Original retained; rejected alternative is not established"
            if concern.decision == CorrectionDecision.RETAIN_UNCERTAIN
            else "Correction applied but requires review"
        )
        text = _escape_review_text(concern.current_text)
        reason = _escape_review_text(concern.reason)
        source = _escape_review_text(concern.segment_id)
        lines.extend([
            f"- Source {source}, raw characters {concern.original_span.start}:"
            f"{concern.original_span.end}: **{text}** — {status}. {reason}",
        ])
    return [*lines, ""]


def _escape_review_text(value: str) -> str:
    text = value.replace("\n", " ").replace("\r", " ")
    for character in ("\\", "`", "*", "_", "[", "]", "<", ">"):
        text = text.replace(character, "\\" + character)
    return text

