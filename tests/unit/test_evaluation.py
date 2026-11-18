from pathlib import Path

import pytest
from pydantic import ValidationError

from voicenote.evaluation import GoldenFixture, evaluate_result
from voicenote.evaluation.schemas import FactCheck, GoldenCase

GOLDEN = Path(__file__).resolve().parents[2] / "evals" / "golden"


def load_fixture(name: str = "finance-en") -> GoldenFixture:
    return GoldenFixture.model_validate_json((GOLDEN / f"{name}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", ["finance-en", "finance-zh", "fund-attribution"])
def test_reference_fixtures_pass(name: str) -> None:
    fixture = load_fixture(name)
    report = evaluate_result(fixture.result, fixture.case)
    assert report.passed
    assert all(score.pass_rate == 1 for score in report.scores.values())


@pytest.mark.parametrize("wrong", ["115%", "50%", "-15%", "+15%", "15%%"])
def test_altered_numeric_value_fails_despite_valid_citation(wrong: str) -> None:
    fixture = load_fixture()
    result = fixture.result.model_dump(mode="json")
    result["notes"]["sections"][0]["bullets"] = [f"Fund A returned {wrong} in Q2 2026."]
    mutated = fixture.result.model_validate(result)
    report = evaluate_result(mutated, fixture.case)
    assert not report.passed
    assert report.scores["provenance"].pass_rate == 1
    assert next(item for item in report.checks if item.id == "fact:return-numeric").passed is False


def test_valid_numeric_value_does_not_match_a_longer_decimal() -> None:
    fixture = load_fixture()
    check = FactCheck(
        id="integer", dimension="numeric", artifact="notes", source_segment_ids=("en-1",),
        must_include=("15",),
    )
    case = fixture.case.model_copy(update={"checks": (check,)})
    data = fixture.result.model_dump(mode="json")
    data["notes"]["sections"][0]["bullets"] = ["Return: 15.5"]
    assert not evaluate_result(fixture.result.model_validate(data), case).passed
    data["notes"]["sections"][0]["bullets"] = ["Return: 15."]
    assert evaluate_result(fixture.result.model_validate(data), case).passed


def test_currency_and_units_are_not_interchangeable() -> None:
    fixture = load_fixture()
    data = fixture.result.model_dump(mode="json")
    data["meeting_minutes"]["sections"][1]["bullets"] = [
        "Analyst Chen believes Acme may reach EUR 2.5 billion revenue if demand recovers."
    ]
    report = evaluate_result(fixture.result.model_validate(data), fixture.case)
    assert not next(item for item in report.checks if item.id == "fact:revenue-unit").passed


def test_attribution_is_checked_against_structured_speaker() -> None:
    fixture = load_fixture()
    data = fixture.result.model_dump(mode="json")
    data["semantic_document"]["items"][1]["speaker"] = "Manager"
    report = evaluate_result(fixture.result.model_validate(data), fixture.case)
    assert not report.scores["attribution"].passed


def test_missing_condition_and_strengthened_view_fail() -> None:
    fixture = load_fixture()
    data = fixture.result.model_dump(mode="json")
    data["executive_brief"]["important_views"][1]["text"] = (
        "Acme will reach USD 2.5 million revenue."
    )
    report = evaluate_result(fixture.result.model_validate(data), fixture.case)
    assert not report.scores["qualification"].passed


def test_explicitly_approved_wording_variant_passes() -> None:
    fixture = load_fixture()
    data = fixture.result.model_dump(mode="json")
    data["executive_brief"]["important_views"][1]["text"] = (
        "Acme could reach USD 2.5 million revenue if demand recovers."
    )
    assert evaluate_result(fixture.result.model_validate(data), fixture.case).passed


def test_qualification_token_cannot_match_inside_an_unrelated_word() -> None:
    fixture = load_fixture()
    data = fixture.result.model_dump(mode="json")
    data["executive_brief"]["important_views"][1]["text"] = (
        "Acme receives payment if demand recovers."
    )
    report = evaluate_result(fixture.result.model_validate(data), fixture.case)
    assert report.scores["qualification"].passed == 0


def test_missing_action_owner_or_deadline_fails() -> None:
    fixture = load_fixture()
    data = fixture.result.model_dump(mode="json")
    data["executive_brief"]["actions"][0]["text"] = "Review the debt schedule."
    report = evaluate_result(fixture.result.model_validate(data), fixture.case)
    assert report.scores["action"].passed == 0


def test_nested_raw_evidence_cannot_silently_diverge() -> None:
    fixture = load_fixture()
    data = fixture.result.model_dump(mode="json")
    data["corrected_transcript"]["raw_transcript"]["segments"][0]["text"] = "Rewritten raw text"
    report = evaluate_result(fixture.result.model_validate(data), fixture.case)
    assert report.scores["source_evidence"].passed == 0


def test_forbidden_claim_is_detected_even_under_an_unrelated_source() -> None:
    fixture = load_fixture()
    data = fixture.result.model_dump(mode="json")
    data["meeting_minutes"]["sections"][0]["bullets"].append("Committee approved buying Acme.")
    report = evaluate_result(fixture.result.model_validate(data), fixture.case)
    assert not report.scores["unsupported_claim"].passed
    assert report.scores["provenance"].pass_rate == 1


def test_fragments_split_across_bullets_do_not_count_as_one_fact() -> None:
    fixture = load_fixture()
    data = fixture.result.model_dump(mode="json")
    data["notes"]["sections"][0]["bullets"] = ["Fund A returned 15%.", "Reporting period Q2 2026."]
    report = evaluate_result(fixture.result.model_validate(data), fixture.case)
    assert not next(item for item in report.checks if item.id == "fact:return-numeric").passed


def test_swapping_sources_invalidates_fact_checks() -> None:
    fixture = load_fixture("fund-attribution")
    data = fixture.result.model_dump(mode="json")
    data["notes"]["sections"][0]["source_segment_ids"] = ["fund-b"]
    report = evaluate_result(fixture.result.model_validate(data), fixture.case)
    assert not next(item for item in report.checks if item.id == "fact:alpha-return").passed


def test_unknown_citation_and_mismatched_raw_evidence_fail_independently() -> None:
    fixture = load_fixture()
    data = fixture.result.model_dump(mode="json")
    data["raw_transcript"]["segments"][0]["text"] = "Different recording"
    data["notes"]["sections"][0]["source_segment_ids"] = ["invented"]
    report = evaluate_result(fixture.result.model_validate(data), fixture.case)
    assert report.scores["source_evidence"].passed == 0
    assert report.scores["provenance"].pass_rate < 1


def test_review_metadata_is_not_mistaken_for_a_generated_claim() -> None:
    fixture = load_fixture()
    data = fixture.result.model_dump(mode="json")
    data["meeting_minutes"]["warnings"] = ["Committee approved buying Acme is a rejected claim."]
    assert evaluate_result(fixture.result.model_validate(data), fixture.case).passed


def test_missing_artifact_fails_even_when_check_only_forbids_content() -> None:
    fixture = load_fixture()
    data = fixture.result.model_dump(mode="json")
    data["meeting_minutes"] = None
    report = evaluate_result(fixture.result.model_validate(data), fixture.case)
    assert not next(item for item in report.checks if item.id == "fact:no-invented-decision").passed


def test_report_does_not_echo_transcript_bodies() -> None:
    fixture = load_fixture()
    report = evaluate_result(fixture.result, fixture.case)
    serialized = report.model_dump_json()
    for segment in fixture.case.source_segments:
        assert segment.text not in serialized


@pytest.mark.parametrize("field", ["source_segments", "checks"])
def test_empty_and_duplicate_golden_definitions_are_rejected(field: str) -> None:
    data = load_fixture().case.model_dump(mode="json")
    data[field] = []
    with pytest.raises(ValidationError):
        GoldenCase.model_validate(data)
    data = load_fixture().case.model_dump(mode="json")
    data[field].append(data[field][0])
    with pytest.raises(ValidationError):
        GoldenCase.model_validate(data)


@pytest.mark.parametrize("change", [
    {"must_include": [], "must_exclude": []},
    {"must_include": [" "]},
    {"source_segment_ids": ["unknown"]},
    {"expected_speaker": "Manager"},
])
def test_invalid_check_definitions_are_rejected(change: dict[str, object]) -> None:
    data = load_fixture().case.model_dump(mode="json")
    data["checks"][0].update(change)
    with pytest.raises(ValidationError):
        GoldenCase.model_validate(data)
