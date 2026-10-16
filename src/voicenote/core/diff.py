"""Human-readable correction audit rendering."""

from __future__ import annotations

from voicenote.core.schemas import CorrectedTranscript


def render_correction_audit_markdown(transcript: CorrectedTranscript) -> str:
    lines = ["# Correction audit", ""]
    if not transcript.corrections:
        lines.extend(["No correction proposals were recorded.", ""])
        return "\n".join(lines)

    lines.extend(
        [
            "| Segment | Original | Corrected | Confidence | Decision | Sensitive | Reason |",
            "| --- | --- | --- | ---: | --- | --- | --- |",
        ]
    )
    for record in transcript.corrections:
        lines.append(
            "| "
            + " | ".join(
                (
                    _escape(record.segment_id),
                    _escape(record.original),
                    _escape(record.corrected),
                    f"{record.confidence:.3f}",
                    record.decision.value,
                    "yes" if record.sensitive else "no",
                    _escape(record.reason),
                )
            )
            + " |"
        )

    if transcript.uncertainties:
        lines.extend(["", "## Retained uncertainties", ""])
        for item in transcript.uncertainties:
            lines.append(
                f"- `{_escape(item.segment_id)}`: **{_escape(item.text)}** "
                f"({item.confidence:.3f}) — {_escape(item.reason)}"
            )
    lines.append("")
    return "\n".join(lines)


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")

