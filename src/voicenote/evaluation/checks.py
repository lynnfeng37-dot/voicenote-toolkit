"""Source-scoped literal assertions, deliberately narrower than factual entailment."""

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass

from voicenote.core.schemas import VoiceNoteResult
from voicenote.evaluation.schemas import (
    Artifact,
    CaseReport,
    CheckOutcome,
    Dimension,
    DimensionScore,
    FactCheck,
    GoldenCase,
)


@dataclass(frozen=True)
class _Observation:
    artifact: Artifact
    path: str
    text: str
    sources: tuple[str, ...]
    speaker: str | None = None


def evaluate_result(result: VoiceNoteResult, case: GoldenCase) -> CaseReport:
    """Evaluate hand-authored checks without sending source or output text to a service."""
    observations = _observations(result)
    outcomes = [_source_evidence(result, case)]
    known = {segment.id for segment in case.source_segments}
    for observation in observations:
        if not observation.text.strip():
            continue
        valid = bool(observation.sources) and set(observation.sources) <= known
        outcomes.append(CheckOutcome(
            id=f"provenance:{observation.path}", dimension=Dimension.PROVENANCE,
            artifact=observation.artifact, passed=valid,
            reason=(
                "Source IDs are present and known." if valid else "Missing or unknown source IDs."
            ),
            observation_paths=(observation.path,),
        ))
    outcomes.extend(_check(result, observations, check) for check in case.checks)
    grouped: dict[str, list[CheckOutcome]] = defaultdict(list)
    for outcome in outcomes:
        grouped[outcome.dimension.value].append(outcome)
    return CaseReport(
        case_id=case.id, passed=all(outcome.passed for outcome in outcomes),
        checks=tuple(outcomes), scores={
            dimension: DimensionScore(
                passed=sum(item.passed for item in items), total=len(items),
                pass_rate=sum(item.passed for item in items) / len(items),
            ) for dimension, items in grouped.items()
        },
    )


def _source_evidence(result: VoiceNoteResult, case: GoldenCase) -> CheckOutcome:
    # Exact text and speaker identity prevent scoring outputs from a different recording.
    actual = (
        [(segment.id, segment.text, segment.speaker) for segment in result.raw_transcript.segments]
        if result.raw_transcript is not None else []
    )
    expected = [(segment.id, segment.text, segment.speaker) for segment in case.source_segments]
    corrected = result.corrected_transcript
    valid = actual == expected and (
        corrected is None or (
            corrected.raw_transcript == result.raw_transcript
            and [segment.id for segment in corrected.segments] == [item[0] for item in expected]
        )
    )
    return CheckOutcome(
        id="source-evidence", dimension=Dimension.SOURCE_EVIDENCE, artifact=Artifact.RAW,
        passed=valid,
        reason="Raw evidence matches the golden case." if valid else "Raw evidence does not match.",
    )


def _check(
    result: VoiceNoteResult, observations: tuple[_Observation, ...], check: FactCheck
) -> CheckOutcome:
    candidates = [item for item in observations if item.artifact == check.artifact]
    if getattr(result, check.artifact.value) is None:
        return _outcome(check, False, "Requested artifact is missing.")
    # Forbidden fragments are checked across the artifact, even under an unrelated citation.
    forbidden = [
        item.path for item in candidates
        if any(_contains(item.text, fragment) for fragment in check.must_exclude)
    ]
    if forbidden:
        return _outcome(check, False, "A forbidden fragment was found.", tuple(forbidden))
    matching = [
        item for item in candidates
        if set(check.source_segment_ids) <= set(item.sources)
        and (check.expected_speaker is None or item.speaker == check.expected_speaker)
        and all(_contains(item.text, fragment) for fragment in check.must_include)
        and (
            not check.must_include_any
            or any(_contains(item.text, fragment) for fragment in check.must_include_any)
        )
    ]
    if (
        check.must_include or check.must_include_any or check.expected_speaker is not None
    ) and not matching:
        return _outcome(check, False, "Required content/attribution is missing from a cited item.")
    return _outcome(check, True, "Golden assertion passed.", tuple(item.path for item in matching))


def _outcome(
    check: FactCheck, passed: bool, reason: str, paths: tuple[str, ...] = ()
) -> CheckOutcome:
    return CheckOutcome(
        id=f"fact:{check.id}", dimension=check.dimension, artifact=check.artifact,
        passed=passed, reason=reason, observation_paths=paths,
    )


def _contains(text: str, fragment: str) -> bool:
    def normalize(value: str) -> str:
        return " ".join(unicodedata.normalize("NFKC", value).casefold().split())

    needle = normalize(fragment)
    prefix = ""
    suffix = ""
    if re.match(r"[+\-]?(?:[0-9]|\.[0-9])", needle):
        prefix = r"(?<![a-z0-9_.+\-])"
    elif needle[0] in "abcdefghijklmnopqrstuvwxyz_":
        prefix = r"(?<![a-z0-9_])"
    if needle[-1] in "0123456789":
        suffix = r"(?![a-z0-9_%]|[.,/][0-9])"
    elif needle[-1] in "abcdefghijklmnopqrstuvwxyz_":
        suffix = r"(?![a-z0-9_])"
    elif needle[-1] == "%":
        suffix = r"(?![a-z0-9_%])"
    return re.search(prefix + re.escape(needle) + suffix, normalize(text)) is not None


def _observations(result: VoiceNoteResult) -> tuple[_Observation, ...]:
    items: list[_Observation] = []
    if result.raw_transcript is not None:
        for index, segment in enumerate(result.raw_transcript.segments):
            items.append(_Observation(
                Artifact.RAW, f"raw_transcript.segments[{index}]", segment.text,
                (segment.id,), segment.speaker,
            ))
    if result.corrected_transcript is not None:
        for index, corrected in enumerate(result.corrected_transcript.segments):
            items.append(_Observation(
                Artifact.CORRECTED, f"corrected_transcript.segments[{index}]",
                corrected.corrected_text, (corrected.id,), corrected.speaker,
            ))
    if result.semantic_document is not None:
        for group in ("items", "entities", "open_questions"):
            for index, item in enumerate(getattr(result.semantic_document, group)):
                items.append(_Observation(
                    Artifact.SEMANTIC, f"semantic_document.{group}[{index}]", item.content,
                    item.source_segment_ids, item.speaker,
                ))
    for artifact, notes in (
        (Artifact.NOTES, result.notes), (Artifact.MINUTES, result.meeting_minutes)
    ):
        if notes is None:
            continue
        for index, section in enumerate(notes.sections):
            for group in ("paragraphs", "bullets"):
                for line, text in enumerate(getattr(section, group)):
                    items.append(_Observation(
                        artifact, f"{artifact.value}.sections[{index}].{group}[{line}]", text,
                        section.source_segment_ids,
                    ))
    if result.executive_brief is not None:
        for group in (
            "what_happened", "important_views", "changes", "decisions", "risks", "actions"
        ):
            for index, point in enumerate(getattr(result.executive_brief, group)):
                items.append(_Observation(
                    Artifact.BRIEF, f"executive_brief.{group}[{index}]", point.text,
                    point.source_segment_ids,
                ))
    return tuple(items)
