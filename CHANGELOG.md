# Changelog

All notable changes will be documented here. This project follows Semantic Versioning once the
public API reaches its first stable release.

## Unreleased

- Added the offline `voicenote-eval` CLI/Python evaluation API, English/Chinese finance golden
  fixtures, source evidence checks, citation checks, and per-dimension content assertion reports.
- Added regressions for numeric/units errors with valid citations, misattribution, strengthened
  qualifications, known unsupported claims, and evaluation CLI exit/report behavior; wired the
  synthetic golden suite into CI.
- Added whole-pipeline local preflight for provider selection, skill names, correction policy,
  cloud consent, SDK/API-key presence, and finance reference availability before transcription.
- Added typed correction review concerns propagated locally into Semantic IR, notes, finance
  minutes, and executive briefs, with source-specific flags and visible Markdown review notices.
- Added regression tests for zero provider calls on invalid configuration, batch-local review
  payloads, raw-coordinate preservation, omitted warnings, and persisted review metadata.
- Added a custom project cover and GitHub social preview export, an offline correction-policy
  demo, a Chinese README, and a prioritized reliability roadmap.
- Clarified citation-validation limits and the data sent to correction and reasoning providers.
- Created the initial package, schemas, provider contracts, pipeline boundaries, renderers,
  Finance Meeting Skill specification, tests, and Agent Skill entrypoint.
- Added explicit local faster-whisper and OpenAI transcription adapters, provider configuration,
  consent gates for cloud processing and model downloads, and structured artifact persistence.
- Added schema-constrained OpenAI correction proposals, deterministic source anchoring, local
  sensitive-entity escalation, curated finance terminology data, and Markdown correction audits.
- Added a schema-constrained OpenAI reasoning adapter, batched source-linked Semantic IR extraction,
  adaptive clean-note generation, deterministic provenance validation, and cited note artifacts.
- Implemented the Finance Meeting Skill with adaptive professional minutes, local uncertainty
  warnings, per-point cited executive briefs, pipeline stages, and JSON/Markdown artifacts.

