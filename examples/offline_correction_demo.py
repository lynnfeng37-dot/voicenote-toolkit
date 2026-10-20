"""Review VoiceNote correction decisions without audio, models, or an API key.

All source text and proposals below are synthetic, hand-authored examples. The demo
exercises the real correction policy, source-span anchoring, audit, and artifact writer.
It does not measure transcription or model accuracy.
"""

from pathlib import Path

from voicenote import __version__
from voicenote.artifacts import persist_result
from voicenote.core.correction import CorrectionPolicy, apply_corrections
from voicenote.core.schemas import (
    AudioSource,
    CorrectionProposal,
    ProcessingStage,
    ProviderMetadata,
    RawTranscript,
    RunManifest,
    TextSpan,
    TranscriptSegment,
    VoiceNoteResult,
)


def main() -> None:
    raw = RawTranscript(
        audio=AudioSource(path="synthetic-demo:no-recording", sha256="0" * 64, size_bytes=0),
        segments=(
            TranscriptSegment(
                id="seg-1", text="We discussed the Sharp ratio.", speaker="Analyst"
            ),
            TranscriptSegment(
                id="seg-2", text="The reported return was 15%.", speaker="Manager"
            ),
        ),
        provider=ProviderMetadata(provider="synthetic-demo", model="hand-authored"),
    )
    proposals = (
        CorrectionProposal(
            segment_id="seg-1", original="Sharp", corrected="Sharpe",
            span=TextSpan(start=17, end=22), confidence=0.97,
            reason="The synthetic terminology reference identifies the Sharpe ratio.",
            category="finance_term", evidence=("Demo reference: Sharpe ratio",),
        ),
        CorrectionProposal(
            segment_id="seg-2", original="15%", corrected="50%",
            span=TextSpan(start=24, end=27), confidence=0.80,
            reason="The proposed percentage has insufficient evidence; review the recording.",
            category="percentage", sensitive=True,
        ),
    )
    corrected = apply_corrections(raw, proposals, CorrectionPolicy())
    result = VoiceNoteResult(
        manifest=RunManifest(
            voicenote_version=__version__, requested_stage=ProcessingStage.CORRECTED,
            completed_stages=(ProcessingStage.TRANSCRIPT, ProcessingStage.CORRECTED),
            providers={"transcription": "synthetic-demo", "correction": "hand-authored"},
            warnings=("Synthetic fixture; no audio or model inference was used.",),
        ),
        raw_transcript=raw, corrected_transcript=corrected,
    )
    run_dir = persist_result(result, Path("output/offline-demo"))
    print("Synthetic example; no audio, model, or network access.")
    print(f"Original:  {raw.segments[0].text}")
    print(f"Corrected: {corrected.segments[0].corrected_text}")
    print(f"Retained:  {corrected.segments[1].corrected_text}")
    print(f"Uncertainties: {len(corrected.uncertainties)}")
    print(f"Artifacts: {run_dir}")


if __name__ == "__main__":
    main()
