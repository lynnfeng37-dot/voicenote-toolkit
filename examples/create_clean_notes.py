"""Generate source-linked clean notes with explicit provider and cloud choices."""

from voicenote import VoiceNote
from voicenote.config import VoiceNoteConfig

config = VoiceNoteConfig(
    transcription_provider="local_whisper",
    correction_provider="openai",
    reasoning_provider="openai",
    allow_cloud_processing=True,
)

result = VoiceNote("meeting.m4a", config=config).process(until="notes")
print(result.notes)
