"""Persist stage artifacts without copying source audio or overwriting prior runs."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel

from voicenote.core.diff import render_correction_audit_markdown
from voicenote.core.schemas import VoiceNoteResult
from voicenote.renderers.markdown import MarkdownRenderer


class OutputFormat(StrEnum):
    JSON = "json"
    MARKDOWN = "markdown"
    BOTH = "both"


def persist_result(
    result: VoiceNoteResult,
    output_dir: Path,
    output_format: OutputFormat = OutputFormat.BOTH,
) -> Path:
    """Write a new run directory and return it; source audio is never copied."""

    run_dir = output_dir.expanduser().resolve() / result.manifest.run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    _write_model(run_dir / "manifest.json", result.manifest)

    if output_format in {OutputFormat.JSON, OutputFormat.BOTH}:
        _write_model(run_dir / "result.json", result)
        if result.raw_transcript is not None:
            _write_model(run_dir / "raw_transcript.json", result.raw_transcript)
        if result.corrected_transcript is not None:
            _write_model(run_dir / "corrected_transcript.json", result.corrected_transcript)
            _write_json_text(
                run_dir / "corrections.json",
                "[\n"
                + ",\n".join(
                    correction.model_dump_json(indent=2)
                    for correction in result.corrected_transcript.corrections
                )
                + "\n]\n",
            )
        if result.semantic_document is not None:
            _write_model(run_dir / "semantic_document.json", result.semantic_document)
        if result.notes is not None:
            _write_model(run_dir / "notes.json", result.notes)
        if result.meeting_minutes is not None:
            _write_model(run_dir / "meeting_minutes.json", result.meeting_minutes)
        if result.executive_brief is not None:
            _write_model(run_dir / "executive_brief.json", result.executive_brief)

    if output_format in {OutputFormat.MARKDOWN, OutputFormat.BOTH}:
        _write_text(run_dir / "result.md", MarkdownRenderer().render(result))
        if result.corrected_transcript is not None:
            _write_text(
                run_dir / "corrections.md",
                render_correction_audit_markdown(result.corrected_transcript),
            )
        if result.notes is not None:
            _write_text(run_dir / "notes.md", MarkdownRenderer().render_notes(result.notes))
        if result.meeting_minutes is not None:
            _write_text(
                run_dir / "meeting_minutes.md",
                MarkdownRenderer().render_minutes(result.meeting_minutes),
            )
        if result.executive_brief is not None:
            _write_text(
                run_dir / "executive_brief.md",
                MarkdownRenderer().render_brief(result.executive_brief),
            )

    return run_dir


def _write_model(path: Path, model: BaseModel) -> None:
    _write_json_text(path, model.model_dump_json(indent=2) + "\n")


def _write_json_text(path: Path, content: str) -> None:
    _write_text(path, content)


def _write_text(path: Path, content: str) -> None:
    # The run directory is newly created with exist_ok=False, so direct creation cannot
    # overwrite a prior artifact and also works on restricted Windows filesystems.
    path.write_text(content, encoding="utf-8", newline="\n")

