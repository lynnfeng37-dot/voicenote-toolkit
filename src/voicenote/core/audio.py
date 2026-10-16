"""Local audio validation without decoding or uploading it."""

from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path

from voicenote.core.schemas import AudioSource
from voicenote.exceptions import InvalidAudioError

SUPPORTED_SUFFIXES = frozenset({".aac", ".flac", ".m4a", ".mp3", ".mp4", ".ogg", ".wav", ".webm"})


def prepare_audio(path: Path) -> AudioSource:
    """Validate a local file and return non-content metadata for providers."""

    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise InvalidAudioError(f"Audio file does not exist: {resolved}")
    if resolved.suffix.lower() not in SUPPORTED_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
        raise InvalidAudioError(
            f"Unsupported audio suffix {resolved.suffix!r}; expected one of {supported}"
        )

    digest = hashlib.sha256()
    with resolved.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)

    media_type, _ = mimetypes.guess_type(resolved.name)
    return AudioSource(
        path=str(resolved),
        media_type=media_type,
        sha256=digest.hexdigest(),
        size_bytes=resolved.stat().st_size,
    )

