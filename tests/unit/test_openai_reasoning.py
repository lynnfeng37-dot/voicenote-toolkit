from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

from voicenote.exceptions import CloudProcessingDisabledError, ProviderError
from voicenote.providers.base import ReasoningRequest
from voicenote.providers.reasoning import OpenAIReasoningConfig, OpenAIReasoningProvider


class Answer(BaseModel):
    value: str


class FakeResponses:
    def __init__(self, parsed: object) -> None:
        self.parsed = parsed
        self.kwargs: dict[str, Any] = {}

    def parse(self, **kwargs: Any) -> object:
        self.kwargs = kwargs
        return SimpleNamespace(output_parsed=self.parsed)


def test_reasoning_requires_explicit_cloud_consent() -> None:
    provider = OpenAIReasoningProvider(client=SimpleNamespace(responses=FakeResponses(None)))
    with pytest.raises(CloudProcessingDisabledError):
        provider.generate_structured(
            ReasoningRequest(task="t", instructions="i", payload={}), Answer
        )


def test_reasoning_uses_responses_parse_without_storage() -> None:
    responses = FakeResponses(Answer(value="ok"))
    provider = OpenAIReasoningProvider(
        OpenAIReasoningConfig(allow_cloud_processing=True),
        client=SimpleNamespace(responses=responses),
    )
    result = provider.generate_structured(
        ReasoningRequest(task="test", instructions="Only evidence", payload={"x": 1}), Answer
    )
    assert result.value == "ok"
    assert responses.kwargs["text_format"] is Answer
    assert responses.kwargs["store"] is False


def test_reasoning_rejects_missing_parsed_output() -> None:
    provider = OpenAIReasoningProvider(
        OpenAIReasoningConfig(allow_cloud_processing=True),
        client=SimpleNamespace(responses=FakeResponses(None)),
    )
    with pytest.raises(ProviderError, match="no parsed output"):
        provider.generate_structured(
            ReasoningRequest(task="t", instructions="i", payload={}), Answer
        )
