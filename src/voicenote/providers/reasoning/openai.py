"""OpenAI Responses adapter for schema-constrained intermediate artifacts."""

from __future__ import annotations

import json
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ConfigDict

from voicenote.exceptions import (
    CloudProcessingDisabledError,
    OptionalDependencyError,
    ProviderError,
)
from voicenote.providers.base import ReasoningProvider, ReasoningRequest

StructuredResult = TypeVar("StructuredResult", bound=BaseModel)


class _ResponsesResource(Protocol):
    def parse(self, **kwargs: Any) -> Any: ...


class OpenAIReasoningClientLike(Protocol):
    responses: _ResponsesResource


class OpenAIReasoningConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    model: str = "gpt-4o-mini"
    allow_cloud_processing: bool = False


class OpenAIReasoningProvider(ReasoningProvider):
    """Generate typed outputs while keeping task construction provider-neutral."""

    name = "openai"

    def __init__(
        self,
        config: OpenAIReasoningConfig | None = None,
        *,
        client: OpenAIReasoningClientLike | None = None,
    ) -> None:
        self.config = config or OpenAIReasoningConfig()
        self._client = client

    def generate_structured(
        self,
        request: ReasoningRequest,
        response_model: type[StructuredResult],
    ) -> StructuredResult:
        if not self.config.allow_cloud_processing:
            raise CloudProcessingDisabledError(
                "OpenAI reasoning is disabled; set allow_cloud_processing explicitly"
            )
        content = json.dumps(
            {"task": request.task, "payload": request.payload, "references": request.references},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        try:
            response = self._get_client().responses.parse(
                model=self.config.model,
                input=[
                    {"role": "system", "content": request.instructions},
                    {"role": "user", "content": content},
                ],
                text_format=response_model,
                store=False,
            )
        except (CloudProcessingDisabledError, OptionalDependencyError):
            raise
        except Exception as error:
            raise ProviderError(f"OpenAI reasoning failed: {error}") from error

        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise ProviderError("OpenAI reasoning returned no parsed output or refused the request")
        if isinstance(parsed, response_model):
            return parsed
        return response_model.model_validate(parsed)

    def _get_client(self) -> OpenAIReasoningClientLike:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI  # type: ignore[import-not-found]
        except ImportError as error:
            raise OptionalDependencyError(
                "OpenAI reasoning requires `pip install voicenote-toolkit[openai]`"
            ) from error
        self._client = OpenAI()
        return self._client

