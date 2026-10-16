# VoiceNote

VoiceNote is an extensible **speech-to-knowledge toolkit** that turns recordings into trustworthy
transcripts, corrected transcripts, readable notes, and optional domain-specific meeting minutes.

> **Status:** pre-alpha. Public interfaces may change before the first release; transcription,
> auditable correction, source-grounded semantic extraction, and clean notes are implemented.

## Principles

- **Correctable:** likely ASR errors can be reviewed and corrected under an explicit confidence
  policy.
- **Traceable:** the raw transcript is immutable, and downstream claims retain links to source
  segments.
- **Extensible:** transcription providers, reasoning providers, renderers, and domain skills are
  independent extension points.

VoiceNote favors fidelity over aggressive rewriting. It must not silently invent a correction when
the evidence is weak, especially for names, dates, percentages, ticker symbols, and financial data.

## Processing ladder

```text
Audio
  -> Raw Transcript
  -> Corrected Transcript + Correction Audit
  -> Semantic Intermediate Representation
  -> Clean Notes
  -> Optional Domain Minutes
  -> Optional Executive Brief
```

Every completed stage remains available in the final result. A later stage never replaces an
earlier artifact.

## Installation for development

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
pytest
```

Provider SDKs are optional:

```bash
python -m pip install -e ".[openai]"
python -m pip install -e ".[local-asr]"
```

Cloud processing is never selected merely because an API key exists. The caller must choose a
cloud provider explicitly.

The local provider also avoids network access by default. If model weights are not already present,
the user must explicitly permit their download.

## Python API

```python
from voicenote import VoiceNote
from voicenote.config import VoiceNoteConfig

note = VoiceNote("meeting.m4a", config=VoiceNoteConfig(
    transcription_provider="local_whisper",
    correction_provider="openai",
    reasoning_provider="openai",
    allow_cloud_processing=True,
))
result = note.process(
    until="notes",
    skill="finance_meeting",
)

print(result.corrected_transcript)
print(result.notes)
```

Providers must be selected explicitly. Calling an unavailable stage raises a focused configuration
error rather than uploading or fabricating content.

## CLI

```bash
voicenote meeting.m4a --provider local_whisper --until transcript
voicenote meeting.m4a --provider local_whisper --allow-model-download
voicenote meeting.m4a --provider openai --allow-cloud --model whisper-1
voicenote meeting.m4a --provider local_whisper --output markdown
voicenote meeting.m4a --provider local_whisper --until corrected \
  --correction-provider openai --allow-cloud --skill finance_meeting
voicenote meeting.m4a --provider local_whisper --until notes \
  --correction-provider openai --reasoning-provider openai --allow-cloud
voicenote meeting.m4a --provider local_whisper --until brief \
  --correction-provider openai --reasoning-provider openai \
  --skill finance_meeting --allow-cloud
```

Installing an optional SDK or local model is always an explicit choice. The notes stage writes the
Semantic IR and clean notes as separate JSON artifacts, plus Markdown with visible source citations.
Finance Meeting minutes and per-point cited executive briefs are also available through the same
pipeline.

## Correction policy

Corrections are represented as structured proposals with source spans, confidence, reason, and
evidence. The default policy is:

| Confidence | Result |
| --- | --- |
| High | Apply automatically and record the change |
| Medium | Apply and surface the change for review |
| Low | Retain the original text and mark it uncertain |

Sensitive entities use stricter thresholds. Overlapping, stale, or source-mismatched proposals are
rejected instead of being guessed into place.

The correction model does not supply trusted character offsets. It returns an exact source token and
occurrence index; VoiceNote locates the span locally, rejects unanchorable suggestions, and applies
the deterministic confidence policy. Finance terminology is loaded from curated JSON reference data
rather than embedded in provider code.

## Finance Meeting Skill

The first official domain skill detects meeting type, extracts finance-specific semantic fields,
and chooses an appropriate structure. It does not force empty sections or use one fixed template.
See [`src/voicenote/skills/finance_meeting`](src/voicenote/skills/finance_meeting) and
[`docs/skills.md`](docs/skills.md).

## Privacy

- Local paths are the default input boundary.
- Provider selection is explicit.
- Audio is not copied into the output directory by default.
- Temporary files must have an explicit lifecycle and cleanup policy.
- Logs must not contain transcript bodies or secrets by default.
- Redaction is a distinct optional stage, never a silent mutation of the source transcript.

See [`docs/privacy.md`](docs/privacy.md) for the planned threat model and provider rules.

## Project layout

```text
src/voicenote/       core package, providers, skills, renderers
tests/               unit, integration, and golden test cases
docs/                architecture, provider, privacy, skill, and evaluation design
.agents/skills/      thin Codex/Agent integration
```

## Roadmap

1. Architecture scaffold and contracts
2. Audio validation plus local/cloud transcription adapters
3. Auditable transcript correction
4. Semantic IR and clean notes (implemented)
5. Finance Meeting minutes and executive brief (implemented)
6. Stable CLI, Python API, evaluation runner, and alpha release

Speaker diarization, REST API, DOCX/HTML export, real-time transcription, and collaboration are
intentionally outside the first MVP.

## Contributing and license

See [`CONTRIBUTING.md`](CONTRIBUTING.md). VoiceNote is licensed under Apache-2.0.

