from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from voicenote.evaluation.cli import evaluate
from voicenote.evaluation.runner import evaluate_fixtures
from voicenote.evaluation.schemas import GoldenFixture, SuiteReport

GOLDEN = Path(__file__).resolve().parents[2] / "evals" / "golden"
cli = typer.Typer()
cli.command()(evaluate)
runner = CliRunner()


def test_cli_scores_suite_and_writes_new_report(tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    result = runner.invoke(cli, [str(GOLDEN), "--output", str(output)])
    assert result.exit_code == 0, result.output
    assert "Cases passed: 3/3" in result.output
    report = SuiteReport.model_validate_json(output.read_text(encoding="utf-8"))
    assert report.total_cases == report.passed_cases == 3


def test_cli_scores_a_saved_result_and_returns_one_on_regression(tmp_path: Path) -> None:
    fixture = GoldenFixture.model_validate_json(
        (GOLDEN / "finance-en.json").read_text(encoding="utf-8")
    )
    data = fixture.result.model_dump(mode="json")
    data["notes"]["sections"][0]["bullets"] = ["Fund A returned 50% in Q2 2026."]
    saved = tmp_path / "result.json"
    saved.write_text(fixture.result.model_validate(data).model_dump_json(), encoding="utf-8")
    output = tmp_path / "failed-report.json"
    result = runner.invoke(cli, [
        str(GOLDEN / "finance-en.json"), "--result", str(saved), "--output", str(output),
    ])
    assert result.exit_code == 1
    assert "fact:return-numeric" in result.output
    assert not SuiteReport.model_validate_json(output.read_text(encoding="utf-8")).passed


def test_existing_reports_are_not_overwritten(tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    output.write_text("keep", encoding="utf-8")
    result = runner.invoke(cli, [str(GOLDEN), "--output", str(output)])
    assert result.exit_code == 2
    assert output.read_text(encoding="utf-8") == "keep"


def test_invalid_json_returns_two_without_dumping_sensitive_input(tmp_path: Path) -> None:
    fixture = tmp_path / "bad.json"
    fixture.write_text('{"private": "do-not-echo"}', encoding="utf-8")
    result = runner.invoke(cli, [str(fixture)])
    assert result.exit_code == 2
    assert "do-not-echo" not in result.output


def test_empty_suite_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No golden"):
        evaluate_fixtures(tmp_path)


def test_suite_rejects_duplicate_case_ids(tmp_path: Path) -> None:
    content = (GOLDEN / "finance-en.json").read_text(encoding="utf-8")
    (tmp_path / "one.json").write_text(content, encoding="utf-8")
    (tmp_path / "two.json").write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="unique"):
        evaluate_fixtures(tmp_path)


def test_result_override_requires_one_case_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="exactly one"):
        evaluate_fixtures(GOLDEN, result_path=tmp_path / "unused.json")
