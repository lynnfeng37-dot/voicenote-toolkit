# Golden regression fixtures

These hand-authored English and Chinese finance fixtures exercise the evaluation engine. They
contain synthetic transcripts and reference outputs, not recordings or measured model predictions.
Passing this suite demonstrates that the specified assertions pass; it is not a model accuracy score.

## Run the suite

From a source checkout with VoiceNote installed:

```bash
python -m voicenote.evaluation evals/golden --output output/evaluation.json
```

The installed `voicenote-eval` command has the same arguments. The `--output` path must be new;
omit it for console-only checks. Reports contain assertion IDs, artifact paths, and dimension scores
without echoing transcript bodies.

Exit codes: `0` = all assertions pass, `1` = a regression was found, `2` = invalid inputs or report
destination. No model SDK, network connection, or API key is needed.

## Score a saved result

Use exactly one fixture and an actual `VoiceNoteResult` JSON file for that same source:

```bash
voicenote-eval evals/golden/finance-en.json --result output/my-run/result.json
```

This overrides the fixture's reference result while preserving its expectations. The result's raw
segment IDs, order, text, and speaker labels must match `case.source_segments`; a different recording
fails the source-evidence check. The raw transcript nested in a corrected artifact must also agree
with the top-level raw artifact, and corrected segments must preserve the source ID sequence.

The same checks are available from Python:

```python
from pathlib import Path
from voicenote.core.schemas import VoiceNoteResult
from voicenote.evaluation import GoldenFixture, evaluate_result

fixture = GoldenFixture.model_validate_json(
    Path("evals/golden/finance-en.json").read_text(encoding="utf-8")
)
result = VoiceNoteResult.model_validate_json(
    Path("output/my-run/result.json").read_text(encoding="utf-8")
)
report = evaluate_result(result, fixture.case)
print(report.passed, report.scores)
```

## Author a fixture

Each JSON file has two keys:

- `case`: an ID, description, source segments, and a non-empty list of checks.
- `result`: a complete serialized `VoiceNoteResult` serving as the synthetic reference output.

A check looks like this:

```json
{
  "id": "conditional-revenue",
  "dimension": "qualification",
  "artifact": "executive_brief",
  "source_segment_ids": ["en-2"],
  "must_include": ["USD 2.5 million", "if demand recovers"],
  "must_include_any": ["may", "could"],
  "must_exclude": ["guaranteed revenue"]
}
```

Required fragments must appear together in one source-linked segment, semantic item, paragraph,
bullet, or brief point. A checklist cannot collect a number from one unrelated bullet and a company
from another to satisfy a single fact. Source IDs in the check must all be attached to that item.
Optional `expected_speaker` is supported for raw/corrected segments and semantic items, which have
structured speaker labels. For prose, explicitly require the attributed name in the same item.

Forbidden fragments are searched across the requested artifact, regardless of the item's citation,
so moving a known bad claim under an unrelated valid source does not hide it. Independently, every
non-empty observed item is checked for present and known source IDs. A missing requested artifact
fails even a forbidden-only check; an existing empty artifact can pass such a check.

Text matching normalizes Unicode compatibility forms, letter case, and whitespace. ASCII word and
numeric boundaries prevent examples such as `15%` matching `115%`, or `may` matching `payment`.
Currency conversions, unit conversions, and paraphrases are not inferred; author explicit permitted
wording with `must_include_any` where appropriate.

## Limits

The dimensions are numeric accuracy, entities, attribution, qualifications, actions, known unsupported
claims, and other content. Reports summarize assertion pass rates, not general precision/recall or
hallucination rates. In particular, an unlisted unsupported claim is not automatically detected.
Human labels and the chosen assertions determine the scope of a case.

Headings, correction proposals, review metadata, and warnings are not scored as generated factual
prose. A syntactically valid citation still cannot establish factual entailment. Review-propagation
and correction-policy behavior have separate tests in `tests/integration/` and `tests/unit/`.

Start from the bundled cases, add domain-specific reference facts, and inspect failures before
loosening an expectation. Do not add private recordings or meeting text to public fixtures.
