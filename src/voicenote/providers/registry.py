"""Explicit provider registration; importing VoiceNote performs no network setup."""

from __future__ import annotations

from typing import Generic, TypeVar

from voicenote.exceptions import ProviderNotConfiguredError

ProviderT = TypeVar("ProviderT")


class ProviderRegistry(Generic[ProviderT]):
    def __init__(self) -> None:
        self._providers: dict[str, ProviderT] = {}

    def register(self, name: str, provider: ProviderT) -> None:
        if not name:
            raise ValueError("Provider name cannot be empty")
        self._providers[name] = provider

    def get(self, name: str) -> ProviderT:
        try:
            return self._providers[name]
        except KeyError as error:
            available = ", ".join(sorted(self._providers)) or "none"
            raise ProviderNotConfiguredError(
                f"Provider {name!r} is not registered; available providers: {available}"
            ) from error

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))

