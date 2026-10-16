from typing import TypeVar, cast

import pytest
from pydantic import BaseModel

from voicenote.core.schemas import SemanticDocument, SemanticItem
from voicenote.exceptions import ProvenanceError
from voicenote.providers.base import ReasoningProvider, ReasoningRequest
from voicenote.skills.finance_meeting.skill import (
    FinanceMeetingSkill,
    GeneratedBriefItem,
    GeneratedExecutiveBrief,
    GeneratedFinanceMinutes,
    GeneratedMinutesSection,
)

T = TypeVar("T", bound=BaseModel)


class FinanceReasoning(ReasoningProvider):
    name = "finance-fixture"

    def __init__(self, source_id: str = "seg-1") -> None:
        self.source_id = source_id
        self.requests: list[ReasoningRequest] = []

    def generate_structured(self, request: ReasoningRequest, response_model: type[T]) -> T:
        del response_model
        self.requests.append(request)
        if request.task == "create_finance_meeting_minutes":
            result = GeneratedFinanceMinutes(
                meeting_type="internal_investment",
                title="Investment Committee",
                sections=[
                    GeneratedMinutesSection(
                        title="Core View",
                        paragraphs=[],
                        bullets=["估值具有吸引力"],
                        source_segment_ids=[self.source_id],
                    ),
                    GeneratedMinutesSection(
                        title="Empty", paragraphs=[], bullets=[], source_segment_ids=[]
                    ),
                ],
                warnings=[],
            )
        else:
            result = GeneratedExecutiveBrief(
                what_happened=[],
                important_views=[
                    GeneratedBriefItem(
                        text="估值具有吸引力", source_segment_ids=[self.source_id]
                    )
                ],
                changes=[], decisions=[], risks=[], actions=[],
            )
        return cast(T, result)


def _document(confidence: float = 0.95) -> SemanticDocument:
    return SemanticDocument(
        meeting_type="internal_investment",
        items=(SemanticItem(
            field="valuation", content="估值具有吸引力",
            source_segment_ids=("seg-1",), confidence=confidence,
        ),),
    )


def test_finance_skill_creates_adaptive_minutes_and_brief() -> None:
    provider = FinanceReasoning()
    skill = FinanceMeetingSkill()
    minutes = skill.organize(_document(), provider)
    brief = skill.create_brief(minutes, _document(), provider)
    assert minutes.meeting_type == "internal_investment"
    assert len(minutes.sections) == 1
    assert brief.important_views[0].source_segment_ids == ("seg-1",)
    assert provider.requests[0].references


def test_finance_skill_adds_local_uncertainty_warning() -> None:
    minutes = FinanceMeetingSkill().organize(_document(0.5), FinanceReasoning())
    assert any("below 0.80" in warning for warning in minutes.warnings)


def test_finance_skill_rejects_unsupported_citations() -> None:
    with pytest.raises(ProvenanceError, match="Unsupported minutes"):
        FinanceMeetingSkill().organize(_document(), FinanceReasoning("invented"))
