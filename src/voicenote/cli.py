"""VoiceNote command-line interface."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from voicenote import __version__
from voicenote.api import VoiceNote
from voicenote.artifacts import OutputFormat, persist_result
from voicenote.config import VoiceNoteConfig
from voicenote.core.schemas import ProcessingStage
from voicenote.exceptions import VoiceNoteError
from voicenote.logging import configure_logging
from voicenote.pipeline import PipelineProviders
from voicenote.providers.factory import (
    build_correction_provider,
    build_reasoning_provider,
    build_transcription_provider,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


def process(
    audio: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    until: Annotated[ProcessingStage, typer.Option()] = ProcessingStage.TRANSCRIPT,
    skill: Annotated[str | None, typer.Option()] = None,
    language: Annotated[str | None, typer.Option()] = None,
    provider: Annotated[
        str | None,
        typer.Option(help="Explicit provider: local_whisper or openai."),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option(help="Provider model name or local model path."),
    ] = None,
    correction_provider: Annotated[
        str | None,
        typer.Option(help="Explicit correction provider: openai or none."),
    ] = None,
    correction_model: Annotated[str | None, typer.Option()] = None,
    reasoning_provider: Annotated[
        str | None, typer.Option(help="Explicit reasoning provider: openai.")
    ] = None,
    reasoning_model: Annotated[str | None, typer.Option()] = None,
    term: Annotated[
        list[str] | None,
        typer.Option("--term", help="Expected term; repeat for multiple terms."),
    ] = None,
    output: Annotated[OutputFormat, typer.Option()] = OutputFormat.BOTH,
    output_dir: Annotated[Path | None, typer.Option()] = None,
    allow_cloud: Annotated[
        bool | None,
        typer.Option(
            "--allow-cloud/--no-allow-cloud",
            help="Authorize sending this recording to the selected cloud provider.",
        ),
    ] = None,
    allow_model_download: Annotated[
        bool | None,
        typer.Option(
            "--allow-model-download/--no-allow-model-download",
            help="Allow the local provider to download missing model weights.",
        ),
    ] = None,
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version_callback, is_eager=True),
    ] = False,
) -> None:
    """Process AUDIO through an explicitly configured provider pipeline."""

    del version
    environment_config = VoiceNoteConfig.from_env()
    config = environment_config.model_copy(
        update={
            "transcription_provider": provider or environment_config.transcription_provider,
            "transcription_model": model or environment_config.transcription_model,
            "correction_provider": correction_provider
            or environment_config.correction_provider,
            "correction_model": correction_model or environment_config.correction_model,
            "reasoning_provider": reasoning_provider or environment_config.reasoning_provider,
            "reasoning_model": reasoning_model or environment_config.reasoning_model,
            "output_dir": output_dir or environment_config.output_dir,
            "allow_cloud_processing": (
                environment_config.allow_cloud_processing
                if allow_cloud is None
                else allow_cloud
            ),
            "allow_model_download": (
                environment_config.allow_model_download
                if allow_model_download is None
                else allow_model_download
            ),
        }
    )
    configure_logging(config.log_level)
    try:
        transcription = build_transcription_provider(config)
        correction = (
            build_correction_provider(config)
            if until != ProcessingStage.TRANSCRIPT
            else None
        )
        reasoning = (
            build_reasoning_provider(config)
            if until in {ProcessingStage.NOTES, ProcessingStage.MINUTES, ProcessingStage.BRIEF}
            else None
        )
        result = VoiceNote(
            audio,
            providers=PipelineProviders(
                transcription=transcription,
                correction=correction,
                reasoning=reasoning,
            ),
            config=config,
        ).process(
            until=until,
            skill=skill,
            language=language,
            terminology=tuple(term or ()),
        )
        run_dir = persist_result(result, config.output_dir, output)
    except VoiceNoteError as error:
        typer.secho(str(error), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from error
    typer.echo(str(run_dir))


def app() -> None:
    """Run the single-command CLI as `voicenote AUDIO [OPTIONS]`."""

    typer.run(process)


if __name__ == "__main__":
    app()

