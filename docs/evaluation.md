# Evaluation

Golden cases represent the full evidence chain:

```text
audio or synthetic transcript fixture
  -> raw transcript
  -> expected correction decisions
  -> expected semantic items
  -> expected notes/minutes
```

Report dimensions separately: transcription fidelity, correction precision, false correction rate,
sensitive-entity accuracy, numeric exact match, entity preservation, information retention,
unsupported claim rate, structural quality, action-item precision/recall, and finance terminology
accuracy.

An incorrect high-confidence edit is more harmful than retaining a doubtful token, so evaluation
weights confident false corrections most heavily. Structural tests should check facts and provenance,
not exact generated prose or heading text.

Correction golden cases should include repeated substrings, mixed Chinese and English, fullwidth
punctuation, numeric near-misses, tickers, dates, valuation multiples, names, terminology variants,
overlapping candidates, and deliberately unanchorable proposals.

Semantic and note golden cases should include missing citations, unknown segment IDs, cross-batch
citations, empty sections, conflicting meeting-type classifications, qualified claims, and numeric
details. Generated prose need not match exactly; every accepted claim must remain source-supported.

Finance-skill evaluation additionally checks meeting classification, omission of unsupported empty
sections, fact-versus-view separation, action-item fidelity, numeric qualifiers, and per-point brief
citations. A concise brief with an unsupported claim fails even when its prose is otherwise useful.

## Implemented reliability regressions

Preflight tests use providers that record calls and a deliberately unreadable input path. Missing
downstream providers, unknown skills, invalid policy settings, absent SDKs/keys, unreadable skill
references, and disabled cloud consent must fail with no ASR, correction, or reasoning calls.
Separate checks verify that unused cloud providers do not block a transcription-only request and
that local preflight does not load models.

Review-propagation tests cover sensitive percentages, applied-but-flagged company names, an earlier
length-changing edit, imported uncertainties without correction records, per-batch scoping, JSON
round trips, and Markdown notices. Scripted reasoning intentionally returns no warning metadata;
the source concerns must survive every stage, including when the model omits uncertain content.
These tests prove metadata retention and policy behavior, not real model accuracy or entailment.

