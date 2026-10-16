# Output modes

Select the stopping level that matches the user's request:

- `transcript`: faithful ASR output with timestamps/speakers when available.
- `corrected`: full corrected transcript plus correction and uncertainty records.
- `notes`: readable, content-led notes that retain meaningful information.
- `minutes`: domain-organized meeting minutes; choose a relevant skill when one exists.
- `brief`: highly compressed changes, decisions, risks, important views, and actions.

When the user asks for a higher compression level, retain the earlier artifacts in the structured
result even if only the final document is displayed. A request for a transcript alone does not
authorize summarization or domain reinterpretation.

