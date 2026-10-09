"""TypedValve — conditional gate wrapping a TypedFilter.

Only runs the wrapped filter when ``predicate(ctx)`` returns True.
Skipped runs return ctx unchanged and record 'skipped' in State.

Elevate routing to a Valve on the Pipeline so branching is
statically inspectable in the pipeline blueprint.
"""

from __future__ import annotations

from typing import Callable, Generic, TypeVar

from .filter import TypedFilter

Ctx = TypeVar("Ctx")


class TypedValve(TypedFilter[Ctx], Generic[Ctx]):
    """A gated filter. Runs ``inner`` only when ``predicate(ctx)`` is True."""

    def __init__(self, inner: TypedFilter[Ctx], predicate: Callable[[Ctx], bool]) -> None:
        self._inner = inner
        self._predicate = predicate
        self._last_skipped = False

    def call(self, ctx: Ctx) -> Ctx:
        if self._predicate(ctx):
            self._last_skipped = False
            return self._inner.call(ctx)
        self._last_skipped = True
        return ctx

    @property
    def last_skipped(self) -> bool:
        return self._last_skipped

    @property
    def name(self) -> str:
        return f"TypedValve({type(self._inner).__name__})"
