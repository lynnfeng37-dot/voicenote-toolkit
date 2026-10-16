"""Load declarative skill manifests without executing arbitrary plugin code."""

from __future__ import annotations

import tomllib
from pathlib import Path

from voicenote.skills.base import SkillManifest, VoiceNoteSkill


def load_manifest(path: Path) -> SkillManifest:
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    return SkillManifest.model_validate(data)


def load_skill(name: str) -> VoiceNoteSkill:
    """Load an explicitly selected built-in skill without executing third-party code."""

    if name == "finance_meeting":
        from voicenote.skills.finance_meeting import create_skill

        return create_skill()
    from voicenote.exceptions import SkillNotFoundError

    raise SkillNotFoundError(f"Unknown or unavailable VoiceNote skill: {name!r}")

