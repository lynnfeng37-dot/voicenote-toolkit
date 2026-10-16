from __future__ import annotations

from pathlib import Path

from voicenote.artifacts import OutputFormat, persist_result
from voicenote.core.correction import CorrectionPolicy, apply_corrections
from voicenote.core.schemas import (
    BriefItem,
    CleanNotes,
    CorrectionProposal,
    ExecutiveBrief,
    MeetingMinutes,
    NoteSection,
    ProcessingStage,
    RawTranscript,
    RunManifest,
    SemanticDocument,
    SemanticItem,
    TextSpan,
    VoiceNoteResult,
)


def test_persist_result_writes_stage_files_without_copying_audio(
    tmp_path: Path,
    raw_transcript: RawTranscript,
) -> None:
    result = VoiceNoteResult(
        manifest=RunManifest(
            run_id="fixed-run",
            voicenote_version="test",
            requested_stage=ProcessingStage.TRANSCRIPT,
            completed_stages=(ProcessingStage.TRANSCRIPT,),
        ),
        raw_transcript=raw_transcript,
    )

    run_dir = persist_result(result, tmp_path, OutputFormat.BOTH)

    assert (run_dir / "manifest.json").is_file()
    assert (run_dir / "result.json").is_file()
    assert (run_dir / "raw_transcript.json").is_file()
    assert (run_dir / "result.md").is_file()
    assert not (run_dir / "meeting.wav").exists()
    assert "夏普币率" in (run_dir / "result.md").read_text(encoding="utf-8")


def test_persist_result_writes_correction_audit(
    tmp_path: Path,
    raw_transcript: RawTranscript,
) -> None:
    corrected = apply_corrections(
        raw_transcript,
        (
            CorrectionProposal(
                segment_id="seg-1",
                original="夏普币率",
                corrected="夏普比率",
                span=TextSpan(start=4, end=8),
                confidence=0.99,
                reason="Terminology",
                category="finance_term",
            ),
        ),
        CorrectionPolicy(),
    )
    result = VoiceNoteResult(
        manifest=RunManifest(
            run_id="corrected-run",
            voicenote_version="test",
            requested_stage=ProcessingStage.CORRECTED,
        ),
        raw_transcript=raw_transcript,
        corrected_transcript=corrected,
    )

    run_dir = persist_result(result, tmp_path, OutputFormat.BOTH)

    assert (run_dir / "corrections.json").is_file()
    assert (run_dir / "corrections.md").is_file()


def test_persist_result_writes_notes_and_semantic_ir(
    tmp_path: Path, raw_transcript: RawTranscript
) -> None:
    corrected = apply_corrections(raw_transcript, (), CorrectionPolicy())
    semantic = SemanticDocument(items=(SemanticItem(
        field="view", content="回报为百分之十", source_segment_ids=("seg-1",),
        confidence=0.9,
    ),))
    notes = CleanNotes(title="笔记", sections=(NoteSection(
        title="观点", bullets=("回报为百分之十",), source_segment_ids=("seg-1",),
    ),))
    result = VoiceNoteResult(
        manifest=RunManifest(
            run_id="notes-run", voicenote_version="test",
            requested_stage=ProcessingStage.NOTES,
        ),
        raw_transcript=raw_transcript, corrected_transcript=corrected,
        semantic_document=semantic, notes=notes,
    )
    run_dir = persist_result(result, tmp_path, OutputFormat.BOTH)
    assert (run_dir / "semantic_document.json").is_file()
    assert (run_dir / "notes.json").is_file()
    assert "Sources: seg-1" in (run_dir / "notes.md").read_text(encoding="utf-8")


def test_persist_result_writes_minutes_and_brief(
    tmp_path: Path, raw_transcript: RawTranscript
) -> None:
    corrected = apply_corrections(raw_transcript, (), CorrectionPolicy())
    section = NoteSection(
        title="Risks", bullets=("估值风险",), source_segment_ids=("seg-1",)
    )
    result = VoiceNoteResult(
        manifest=RunManifest(
            run_id="brief-run", voicenote_version="test",
            requested_stage=ProcessingStage.BRIEF,
        ),
        raw_transcript=raw_transcript,
        corrected_transcript=corrected,
        meeting_minutes=MeetingMinutes(
            skill="finance_meeting", meeting_type="internal_investment",
            sections=(section,),
        ),
        executive_brief=ExecutiveBrief(
            risks=(BriefItem(text="估值风险", source_segment_ids=("seg-1",)),)
        ),
    )
    run_dir = persist_result(result, tmp_path, OutputFormat.BOTH)
    assert (run_dir / "meeting_minutes.json").is_file()
    assert (run_dir / "meeting_minutes.md").is_file()
    assert (run_dir / "executive_brief.json").is_file()
    assert "Sources: seg-1" in (
        run_dir / "executive_brief.md"
    ).read_text(encoding="utf-8")

