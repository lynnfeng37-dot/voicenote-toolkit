"""Load curated terminology as data rather than embedding it in provider prompts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from voicenote.core.schemas import TerminologyEntry

_TERMINOLOGY_ADAPTER = TypeAdapter(tuple[TerminologyEntry, ...])


def load_terminology(path: Path) -> tuple[TerminologyEntry, ...]:
    with path.open("r", encoding="utf-8") as stream:
        data: Any = json.load(stream)
    return _TERMINOLOGY_ADAPTER.validate_python(data)


def finance_terminology_path() -> Path:
    return (
        Path(__file__).parents[1]
        / "skills"
        / "finance_meeting"
        / "references"
        / "terminology.json"
    )


def load_finance_terminology() -> tuple[TerminologyEntry, ...]:
    return load_terminology(finance_terminology_path())


def ad_hoc_terminology(terms: tuple[str, ...]) -> tuple[TerminologyEntry, ...]:
    return tuple(TerminologyEntry(canonical=term) for term in terms if term.strip())

