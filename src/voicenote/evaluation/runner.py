"""Load explicit fixtures or saved results and aggregate deterministic reports."""

from pathlib import Path

from voicenote.core.schemas import VoiceNoteResult
from voicenote.evaluation.checks import evaluate_result
from voicenote.evaluation.schemas import GoldenFixture, SuiteReport


def evaluate_fixtures(path: Path, *, result_path: Path | None = None) -> SuiteReport:
    if result_path is not None and not path.is_file():
        raise ValueError("--result requires exactly one golden fixture file")
    paths = sorted(path.rglob("*.json")) if path.is_dir() else [path]
    if not paths:
        raise ValueError("No golden fixtures found")
    fixtures = [
        GoldenFixture.model_validate_json(item.read_text(encoding="utf-8")) for item in paths
    ]
    ids = [fixture.case.id for fixture in fixtures]
    if len(ids) != len(set(ids)):
        raise ValueError("Golden case IDs must be unique across the suite")
    override = (
        VoiceNoteResult.model_validate_json(result_path.read_text(encoding="utf-8"))
        if result_path is not None else None
    )
    reports = tuple(
        evaluate_result(override if override is not None else fixture.result, fixture.case)
        for fixture in fixtures
    )
    passed = sum(report.passed for report in reports)
    return SuiteReport(
        passed=passed == len(reports), passed_cases=passed, total_cases=len(reports), cases=reports
    )
