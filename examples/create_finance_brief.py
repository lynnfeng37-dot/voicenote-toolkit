"""Run the complete Finance Meeting compression ladder."""

from voicenote import VoiceNote
from voicenote.config import VoiceNoteConfig

config = VoiceNoteConfig(
    transcription_provider="local_whisper",
    correction_provider="openai",
    reasoning_provider="openai",
    allow_cloud_processing=True,
)

result = VoiceNote("investment-meeting.m4a", config=config).process(
    until="brief", skill="finance_meeting"
)
print(result.meeting_minutes)
print(result.executive_brief)
