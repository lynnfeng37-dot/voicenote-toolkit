# Domain skills

A VoiceNote domain skill consumes `SemanticDocument` and produces structured minutes. It must not
transcribe audio, silently alter a transcript, or duplicate provider code.

Each skill declares a name, version, compatible semantic IR version, supported meeting types,
semantic fields, and reference files in `skill.toml`. Reference materials are retrieval, evaluation,
and organization inputs; they are not assumed to be model training data.

The first official skill is `finance_meeting`. It classifies the meeting before selecting an output
structure, omits empty sections, separates facts from attributed views and inference, and applies
extra scrutiny to numbers and financial entities.

Third-party executable plugin loading is intentionally deferred. During the MVP, skills are built
in or registered explicitly so installing a data-only skill cannot execute arbitrary code.

## Finance Meeting implementation

`FinanceMeetingSkill` receives only source-linked Semantic IR. It loads the declared Markdown
references, asks the configured reasoning provider for schema-constrained minutes, removes empty
sections, normalizes unsupported classifications to `unknown_finance`, and rejects citations absent
from the IR. Local warnings surface ambiguous meeting type and semantic items below 0.80 confidence.

Its Executive Brief is a separate compression pass over the validated minutes and IR. Every brief
point carries its own source segment IDs; unsupported or citation-free points fail closed.

