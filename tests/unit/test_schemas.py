import pytest
from pydantic import ValidationError

from voicenote.core.schemas import TextSpan, TranscriptSegment


def test_text_span_must_have_positive_width() -> None:
    with pytest.raises(ValidationError):
        TextSpan(start=2, end=2)


def test_segment_end_cannot_precede_start() -> None:
    with pytest.raises(ValidationError):
        TranscriptSegment(id="seg", text="hello", start_seconds=5, end_seconds=4)

