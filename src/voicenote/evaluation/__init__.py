"""Offline, human-specified regression checks for saved VoiceNote artifacts."""

from voicenote.evaluation.checks import evaluate_result
from voicenote.evaluation.schemas import CaseReport, GoldenCase, GoldenFixture

__all__ = ["CaseReport", "GoldenCase", "GoldenFixture", "evaluate_result"]
