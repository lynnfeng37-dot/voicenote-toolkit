---
name: voicenote
description: Process user-provided recordings into traceable transcripts, corrected transcripts, clean notes, finance meeting minutes, or executive briefs with the VoiceNote package. Use for VoiceNote audio workflows; do not use for generic audio editing or voice generation.
---

# VoiceNote

Use the repository's `voicenote` package as the processing engine. Do not reproduce transcription,
correction, or finance logic inside this skill.

## Workflow

1. Confirm the requested stopping level from the user's wording; use the least compressed level that
   satisfies the request. Read [references/output-modes.md](references/output-modes.md) when the mode
   is unclear or the user requests multiple artifacts.
2. Inspect provider configuration before processing. Never infer permission to upload audio from the
   presence of an API key. If only cloud processing is available, obtain the user's explicit choice
   of that provider before sending the recording.
3. Invoke the installed package through its Python API or CLI. Keep the raw transcript and correction
   audit in the result even when the user primarily requested notes or minutes.
4. Use `finance_meeting` only for investment, asset-management, company-research, roadshow, strategy,
   or portfolio-review content. Otherwise use general notes or no domain skill.
5. Report uncertain sensitive entities instead of resolving them from guesswork. This includes names,
   companies, tickers, dates, percentages, monetary values, multiples, and financial metrics.
6. Return the requested artifact and briefly disclose provider boundary, unresolved uncertainties,
   and the location of any saved outputs. Do not expose secrets or full provider payloads.

Preserve user recordings. Do not delete, move, overwrite, transcode in place, or retain additional
copies unless the user requested that action. Temporary derivatives follow the package cleanup policy.

