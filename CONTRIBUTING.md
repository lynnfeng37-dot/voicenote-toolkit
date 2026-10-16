# Contributing to VoiceNote

VoiceNote welcomes narrowly scoped issues and pull requests. The project is pre-alpha, so discuss
large API changes before implementing them.

## Development setup

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
pytest
ruff check .
mypy src/voicenote
```

## Design expectations

- Never mutate or silently rewrite the raw transcript.
- Preserve provenance for corrections and extracted claims.
- Add tests for confidence thresholds and sensitive entities.
- Keep provider-specific SDKs behind optional dependencies.
- Do not commit private recordings, API keys, or real meeting content.
- Use synthetic, public-domain, or explicitly anonymized evaluation fixtures.

New domain skills should declare their semantic fields and references without changing the core
pipeline. See `docs/skills.md`.

