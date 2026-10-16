"""Renderer interface."""

from abc import ABC, abstractmethod

from voicenote.core.schemas import VoiceNoteResult


class Renderer(ABC):
    @abstractmethod
    def render(self, result: VoiceNoteResult) -> str:
        """Render without changing any structured artifact."""

