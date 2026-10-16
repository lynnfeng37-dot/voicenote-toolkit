"""Finance Meeting Skill metadata."""

from pathlib import Path
from typing import TYPE_CHECKING

from voicenote.skills.base import SkillManifest
from voicenote.skills.loader import load_manifest

if TYPE_CHECKING:
    from voicenote.skills.finance_meeting.skill import FinanceMeetingSkill


def manifest() -> SkillManifest:
    return load_manifest(Path(__file__).with_name("skill.toml"))


def create_skill() -> "FinanceMeetingSkill":
    from voicenote.skills.finance_meeting.skill import FinanceMeetingSkill

    return FinanceMeetingSkill()


__all__ = ["create_skill", "manifest"]

