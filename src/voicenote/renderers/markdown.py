"""Human-readable projection of available artifacts."""

from voicenote.core.schemas import (
    BriefItem,
    CleanNotes,
    ExecutiveBrief,
    MeetingMinutes,
    NoteSection,
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
        if result.meeting_minutes is not None:
            lines.extend(["## Meeting minutes", ""])
            lines.extend(_render_sections(result.meeting_minutes.sections))
        if result.executive_brief is not None:
            lines.extend(["## Executive brief", ""])
            lines.extend(_render_brief_groups(result.executive_brief))
        return "\n".join(lines).rstrip() + "\n"

    def render_notes(self, notes: CleanNotes) -> str:
        lines = [f"# {notes.title or 'Clean Notes'}", ""]
        lines.extend(_render_sections(notes.sections))
        return "\n".join(lines).rstrip() + "\n"

    def render_minutes(self, minutes: MeetingMinutes) -> str:
        lines = [f"# {minutes.title or 'Finance Meeting Minutes'}", ""]
        lines.extend([f"Meeting type: `{minutes.meeting_type}`", ""])
        lines.extend(_render_sections(minutes.sections))
        if minutes.warnings:
            lines.extend(["## Warnings", ""])
            lines.extend(f"- {warning}" for warning in minutes.warnings)
        return "\n".join(lines).rstrip() + "\n"

    def render_brief(self, brief: ExecutiveBrief) -> str:
        lines = ["# Executive Brief", ""]
        lines.extend(_render_brief_groups(brief))
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
        for item in items
    ] + [""]

