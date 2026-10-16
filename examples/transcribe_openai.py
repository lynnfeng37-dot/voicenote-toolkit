"""Transcribe with OpenAI only after explicit cloud-processing consent."""

from pathlib import Path

from voicenote import VoiceNote
from voicenote.artifacts import persist_result
from voicenote.config import VoiceNoteConfig

config = VoiceNoteConfig(
    transcription_provider="openai",
    transcription_model="whisper-1",
    allow_cloud_processing=True,
)

result = VoiceNote("meeting.m4a", config=config).process(until="transcript")
output_directory = persist_result(result, Path("output"))
print(output_directory)

