# Provider design

VoiceNote defines three capabilities:

- `TranscriptionProvider` produces faithful raw segments.
- `CorrectionProvider` proposes auditable edits but cannot decide policy or mutate text.
- `ReasoningProvider` returns schema-constrained semantic objects.

Provider adapters must map vendor errors to VoiceNote errors, record provider/model metadata, and
avoid logging request bodies. Optional SDKs belong in packaging extras. Tests must use fake
providers unless a test is explicitly marked as an external integration test.

Provider discovery is explicit. Importing `voicenote` must not inspect keys, contact a service, or
download a model. Local and cloud providers can coexist in one installation without changing the
pipeline.

## Local preflight

Before audio hashing or transcription, the pipeline checks every requested provider and the selected
skill. Missing correction/reasoning providers, unknown skills, invalid correction thresholds, and
unavailable finance references fail at this point. Only providers needed for the stopping stage
are checked.

Providers expose an optional `validate_configuration()` hook with a no-op default for existing
custom providers. Implementations must keep it local: no service requests or model loading. The
built-in cloud adapters check consent, SDK presence, and `OPENAI_API_KEY` presence unless an explicit
client was injected. The local adapter checks the SDK without acquiring model weights. Actual
credential validity, remote availability, model-cache state, and hardware compatibility remain
runtime checks.

## Built-in transcription providers

`local_whisper` lazily loads faster-whisper. It passes `local_files_only=True` unless model download
permission was explicitly enabled. The audio stays local; the first permitted model acquisition may
contact the configured model registry.

`openai` checks the cloud-processing consent flag before opening the audio file for the SDK call.
The default model is `whisper-1` because VoiceNote's raw artifact benefits from its verbose segment
timestamps. Other transcription models remain configurable. Speaker diarization selects the
dedicated diarization model and maps returned speaker segments without rewriting their text.

The OpenAI file adapter rejects oversized inputs before upload. Chunking and compression will be a
separate preprocessing feature so the adapter never silently changes audio.

## Correction provider

The OpenAI correction adapter uses schema-constrained output. It sends transcript segments and the
selected terminology references, not the audio file. Cloud consent is still required because meeting
text may be just as sensitive as the recording.

The model proposes exact source strings and occurrence indexes rather than authoritative character
offsets. VoiceNote anchors each proposal locally, marks locally detected sensitive entities, enriches
evidence with matching reference terms, and then passes proposals to the deterministic correction
policy. Unknown segments, missing occurrences, overlaps, and stale source text fail closed.

## Reasoning provider

The OpenAI reasoning adapter uses the Responses API with typed structured output. It sends corrected
text or Semantic IR—not audio—and disables response storage. Semantic extraction is batched on
segment boundaries. VoiceNote then rejects missing citations, citations outside the active batch,
and note citations not supported by the Semantic IR. Cloud consent is checked before every call.

Extraction requests also contain correction `review_concerns` for the active segment batch. These
distinguish retained uncertain text from applied-but-flagged edits; rejected alternatives are labeled
as proposals, not facts. Later organization requests receive the concerns through the Semantic IR.
Local code, rather than model-authored warning text, carries the metadata into the final artifacts.

