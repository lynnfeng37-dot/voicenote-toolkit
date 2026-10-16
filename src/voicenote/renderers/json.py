"""Complete machine-readable output."""

from voicenote.core.schemas import VoiceNoteResult
from voicenote.renderers.base import Renderer


class JsonRenderer(Renderer):
    def render(self, result: VoiceNoteResult) -> str:
        return result.model_dump_json(indent=2)

