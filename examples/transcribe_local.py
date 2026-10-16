"""Transcribe locally with an already-cached faster-whisper model."""

from pathlib import Path

from voicenote import VoiceNote
from voicenote.artifacts import persist_result
from voicenote.config import VoiceNoteConfig

config = VoiceNoteConfig(
    transcription_provider="local_whisper",
    transcription_model="small",
    allow_model_download=False,
)

result = VoiceNote("meeting.m4a", config=config).process(until="transcript")
output_directory = persist_result(result, Path("output"))
print(output_directory)

