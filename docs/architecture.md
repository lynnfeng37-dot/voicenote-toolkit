# Architecture

VoiceNote is organized around immutable stage artifacts and explicit provider boundaries.

```text
local audio
  -> TranscriptionProvider
  -> RawTranscript (immutable evidence)
  -> CorrectionProvider proposals
  -> deterministic CorrectionPolicy
  -> CorrectedTranscript + audit records
  -> ReasoningProvider
  -> SemanticDocument (source-linked IR)
  -> general notes or domain Skill
  -> structured output
  -> renderer
```

## Invariants

1. Raw transcript text is never mutated by correction, extraction, skills, or renderers.
2. A correction is applied only against an exact source span.
3. Conflicting, overlapping, stale, or unknown-segment corrections fail closed.
4. Sensitive entities have stricter thresholds than ordinary words.
5. Semantic claims retain source segment IDs.
6. Renderers format artifacts but do not infer new information.
7. Cloud access requires explicit provider selection and configuration.
8. A failed later stage does not invalidate already persisted earlier artifacts.
9. Every non-empty note section cites transcript segments already represented in the Semantic IR.

## Layer boundaries

`core` owns provider-independent schemas and deterministic transformations. `providers` adapt external
models into those schemas. `skills` classify and organize the semantic IR. `renderers` project
structured results into presentation formats. The future REST API will depend on these layers; none
of them will depend on the REST API.

Clean-note generation is deliberately two-step. Extraction converts bounded corrected-transcript
batches into a source-linked `SemanticDocument`; note generation can reorganize that document but
cannot introduce new source IDs. Both boundaries are schema-constrained, followed by deterministic
local provenance checks.

The Finance Meeting Skill consumes that validated IR and produces adaptive professional minutes.
The optional executive-brief pass consumes both IR and minutes, with citations attached to each
individual brief point rather than to the document as a whole.

## Versioning

Package, public Python API, and semantic IR versioning are distinct. Skills declare the IR version
they accept. Schema migrations will be explicit once persisted artifacts exist in the wild.

