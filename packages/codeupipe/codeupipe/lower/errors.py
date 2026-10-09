"""
Export error types.

The export never emits a stub for something it cannot handle. It fails loud,
fails early, and points at the exact source location.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple


__all__ = [
    "UnsupportedFilterShape",
    "UnsupportedSourceLanguage",
    "UnaccountedConstructs",
    "InvalidEmittedCode",
    "MultipleLoweredFunctions",
]


@dataclass
class UnsupportedFilterShape(Exception):
    """Raised when the AST rewriter encounters something it cannot lower.

    Examples:
        * Dynamic payload keys: ``payload.get(some_variable)``
        * Use of ``State``, ``MutablePayload``, or ``SharedPayload`` inside
          a filter body.
        * Streaming shapes reached during v1 MVP (deferred to M4).

    Attributes:
        filter_name: The Filter class (or function) whose body triggered this.
        method_name: The method being lowered — usually ``"call"``.
        line: 1-based line number in the ORIGINAL source.
        col: 0-based column offset in the ORIGINAL source.
        node_kind: The ``ast`` node type name (e.g. ``"Attribute"``).
        suggestion: One-line hint pointing at a mechanical rewrite the human
            can perform to make the filter exportable.
    """

    filter_name: str
    method_name: str
    line: int
    col: int
    node_kind: str
    suggestion: str

    def __str__(self) -> str:  # pragma: no cover — trivial formatting
        return (
            f"{self.filter_name}.{self.method_name} "
            f"at line {self.line}:{self.col} — "
            f"cannot lower {self.node_kind}. "
            f"Hint: {self.suggestion}"
        )


@dataclass
class UnsupportedSourceLanguage(Exception):
    """Raised when import-consume receives sources outside supported languages."""

    source_ref: str
    detected_language: str
    supported_languages: tuple
    suggestion: str

    def __str__(self) -> str:  # pragma: no cover — trivial formatting
        supported = ", ".join(self.supported_languages)
        return (
            f"{self.source_ref} — unsupported source language '{self.detected_language}'. "
            f"Supported consume languages: {supported}. "
            f"Hint: {self.suggestion}"
        )


@dataclass
class UnaccountedConstructs(Exception):
    """Raised when a conversion run finishes with constructs in no terminal state.

    This is the E1 invariant. Every construct the converter saw must end up
    ``converted``, ``quarantined``, or ``ignored``. A construct still
    ``pending`` at the end means the converter walked past code without
    deciding anything about it — which, before this check existed, was
    indistinguishable from a clean run.

    Attributes:
        locations: ``path:line name`` for every unaccounted construct. The
            whole point is naming them; a count alone is not actionable.
    """

    locations: Tuple[str, ...] = field(default_factory=tuple)

    def __str__(self) -> str:
        listed = "\n  ".join(self.locations)
        return (
            f"{len(self.locations)} construct(s) finished in no terminal state "
            f"(neither converted, quarantined, nor ignored):\n  {listed}\n"
            "Every construct must be accounted for — silently dropping code is "
            "the failure mode this check exists to prevent."
        )


@dataclass
class InvalidEmittedCode(Exception):
    """Raised when the export emits code that cannot load or resolve its own names.

    A filter whose body references an undefined name parses and imports, and
    fails only when called, so nothing else catches it. Emitted code that
    cannot run cannot pass anyone's test suite.

    Attributes:
        problems: ``path:line name — description`` per defect. All of them, not
            just the first: a converter emitting broken code usually emits
            several, and surfacing one at a time makes fixing them a guessing
            game.
    """

    problems: Tuple[str, ...] = field(default_factory=tuple)

    def __str__(self) -> str:
        listed = "\n  ".join(self.problems)
        return (
            f"{len(self.problems)} problem(s) in emitted code:\n  {listed}\n"
            "Emitted code must parse and resolve every name it uses."
        )


@dataclass
class MultipleLoweredFunctions(Exception):
    """Raised when several lowered functions target the same module path.

    Each lowered function renders a COMPLETE replacement module, so two of them
    for one path are two conflicting whole-file rewrites. Emitting both would
    leave the caller to pick one, which is a silent wrong answer.

    Whole-module conversion — lowering every function in a module into a single
    coherent replacement — is tracked separately. Until then, convert one
    function at a time by setting ``target_function``.

    Attributes:
        collisions: ``(path, (function, ...))`` per conflicting module.
    """

    collisions: Tuple[Tuple[str, Tuple[str, ...]], ...] = field(default_factory=tuple)

    def __str__(self) -> str:
        listed = "\n  ".join(
            f"{path}: {', '.join(fns)}" for path, fns in self.collisions
        )
        return (
            "Several functions lowered into the same module path, and each "
            "renders a complete replacement:\n  " + listed + "\n"
            "Set target_function to convert one at a time until whole-module "
            "conversion lands."
        )
