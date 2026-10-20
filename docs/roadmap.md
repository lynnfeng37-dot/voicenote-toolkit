# Release priorities and current limits

The implementation is pre-alpha. The checks below describe the current code and the next
engineering milestones, not guarantees about model output quality.

## Next engineering milestones

Completed in the current reliability update:

- Whole-request preflight for selected providers, skill names, correction thresholds, cloud consent,
  installed SDKs, environment API-key presence, and readable finance reference files.
- Local propagation of retained uncertainties and applied-but-flagged corrections through Semantic
  IR, notes, minutes, and brief points, with visible Markdown review notices.

| Priority | Update | Acceptance criteria |
| --- | --- | --- |
| P0 | Strengthen content verification | Golden fixtures measure numbers, attribution, qualifiers, and unsupported claims; valid source IDs alone do not count as factual verification. |
| P1 | Save stage checkpoints and support resume | A later-stage provider error leaves completed artifacts available without retranscribing audio. |
| P1 | Cover long inputs end to end | Extraction and later organization stages handle large IR inputs; oversized individual segments have explicit handling. |
| P1 | Verify packaging and provider compatibility | Build and install a wheel in a clean environment; verify bundled skill references and supported SDK versions. |
| P2 | Add provider and domain extensions | Add local reasoning and new domain skills behind the existing interfaces after the reliability milestones. |

## What validation currently proves

Correction proposals are checked against exact source spans and cannot overlap. The policy decides
whether to apply a proposal or retain an uncertain token. Generated semantic items and non-empty
note sections must cite known source IDs; finance minutes and individual brief points are also
checked against source IDs present in the Semantic IR.

These checks validate references, not factual entailment. A model can cite a real segment while
misstating its content. Confidence scores are model estimates, not calibrated probabilities.

Extraction sends corrected text with review concerns scoped to the active batch. Semantic IR keeps
the full concern list, even if a model omits the affected content. Local code attaches the relevant
concerns to every item, section, and brief point citing a flagged segment, and renderers expose
them in Markdown. Flags are conservative at segment level: they do not assert that every statement
in a flagged section is uncertain. This metadata does not prove that model prose obeys it; content
verification remains the next P0 milestone.

Preflight performs no network or model calls. It cannot verify API-key validity, remote model
availability, GPU compatibility, or the presence of cached model weights. Unused providers are not
validated for a shorter requested stage. Custom providers can implement `validate_configuration()`
to check their own local prerequisites.

The pipeline returns a result after the requested stages finish. The CLI then persists it, so an
intermediate failure currently prevents a new completed run directory from being written.
Extraction is batched by segment boundaries; subsequent organization currently uses one request
per stage, and a single very long segment is not split.

## Publication improvements

- Completed: custom cover, corrected setup instructions, an offline correction-policy demo, and
  an English README with a Chinese companion.
- Pending: repository Topics, social preview upload in GitHub settings, a recorded real-input demo,
  and an alpha release after packaging verification.

See [the evaluation design](evaluation.md) and [architecture](architecture.md).
