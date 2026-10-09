"""TypedTap — read-only observer of a typed payload.

Taps must not mutate ctx. Removing every Tap must yield identical
pipeline output — the manifesto invariant, preserved.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

Ctx = TypeVar("Ctx")


class TypedTap(Generic[Ctx], ABC):
    """Observe a ctx without mutating it. Errors are swallowed by the pipeline."""

    @abstractmethod
    def observe(self, ctx: Ctx) -> None:
        """Look at ctx. Do not modify it."""

    @property
    def name(self) -> str:
        return type(self).__name__
