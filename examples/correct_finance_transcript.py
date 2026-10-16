"""Transcribe locally, then send only transcript text for explicit cloud correction."""

from pathlib import Path

from voicenote import VoiceNote
from voicenote.artifacts import persist_result
from voicenote.config import VoiceNoteConfig

config = VoiceNoteConfig(
    transcription_provider="local_whisper",
    transcription_model="small",
    correction_provider="openai",
    correction_model="gpt-4o-mini",
    allow_cloud_processing=True,
    allow_model_download=False,
)

result = VoiceNote("finance-meeting.m4a", config=config).process(
    until="corrected",
    skill="finance_meeting",
)
output_directory = persist_result(result, Path("output"))
print(output_directory)

