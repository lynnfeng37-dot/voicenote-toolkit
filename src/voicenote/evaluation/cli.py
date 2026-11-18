"""A separate evaluation command leaves the audio-processing CLI unchanged."""

from pathlib import Path
from typing import Annotated

import typer

from voicenote.evaluation.runner import evaluate_fixtures


def evaluate(
    fixtures: Annotated[Path, typer.Argument(exists=True, readable=True)],
    result: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    output: Annotated[
        Path | None, typer.Option(help="New JSON report path; never overwrites.")
    ] = None,
) -> None:
    """Check synthetic FIXTURES, or score a saved --result against one fixture's expectations."""
    try:
        report = evaluate_fixtures(fixtures, result_path=result)
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(report.model_dump_json(indent=2) + "\n")
    except (ValueError, OSError) as error:
        typer.echo(
            f"Invalid evaluation input or report destination ({type(error).__name__}). "
            "Check fixture/result JSON, unique IDs, and that --output does not already exist.",
            err=True,
        )
        raise typer.Exit(code=2) from error
    for case in report.cases:
        passed = sum(check.passed for check in case.checks)
        status = "PASS" if case.passed else "FAIL"
        typer.echo(f"{case.case_id}: {status} ({passed}/{len(case.checks)})")
        for check in case.checks:
            if not check.passed:
                typer.echo(f"  {check.id} [{check.dimension.value}]: {check.reason}")
    typer.echo(f"Cases passed: {report.passed_cases}/{report.total_cases}")
    if not report.passed:
        raise typer.Exit(code=1)


def app() -> None:
    typer.run(evaluate)
