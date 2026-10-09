"""TypedFilter — the typed processing unit.

Same contract as ``Filter``, but the input/output IS your Ctx type
(a dataclass, TypedDict, Pydantic model, or anything else). No dict.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

Ctx = TypeVar("Ctx")


class TypedFilter(Generic[Ctx], ABC):
    """A payload processor over a typed context ``Ctx``."""

    @abstractmethod
    def call(self, ctx: Ctx) -> Ctx:
        """Transform ctx and return the next ctx."""

    @property
    def name(self) -> str:
        return type(self).__name__
