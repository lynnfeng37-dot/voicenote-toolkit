"""Interface consumed by domain-specific organization skills."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict

from voicenote.core.schemas import ExecutiveBrief, MeetingMinutes, SemanticDocument
from voicenote.providers.base import ReasoningProvider


class SkillManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    version: str
    description: str
    ir_version: str
    meeting_types: tuple[str, ...]
    semantic_fields: tuple[str, ...]
    reference_files: tuple[str, ...] = ()


class VoiceNoteSkill(ABC):
    """Organize semantic IR; skills never transcribe audio or rewrite source text."""

    manifest: SkillManifest

    @abstractmethod
    def organize(
        self,
        document: SemanticDocument,
        provider: ReasoningProvider,
    ) -> MeetingMinutes:
        """Create domain minutes grounded in source-linked semantic items."""

    @abstractmethod
    def create_brief(
        self,
        minutes: MeetingMinutes,
        document: SemanticDocument,
        provider: ReasoningProvider,
    ) -> ExecutiveBrief:
        """Compress minutes while retaining per-point source links."""

