"""Typed pipeline — compile-time schema (via type hints) for CUP.

Parallel API to codeupipe.core.Pipeline:
- Same seven primitives (Filter, Tap, Valve, Hook, State, Payload, Pipeline)
- ``Ctx`` is your payload class, known at authoring time
- No dict — the payload IS the type

Dynamic escape hatch: use ``Ctx = dict`` (or ``Ctx = Any``) if you truly need
a dynamic bag of keys. That path just falls back to the existing dict-based
mental model.

Python's runtime type system means these gains are *ergonomic*, not
performance-shattering — no monomorphization at runtime. But the API is
identical across runtimes, which is the polyglot promise.
"""

from .filter import TypedFilter
from .hook import TypedHook
from .pipeline import TypedPipeline
from .tap import TypedTap
from .valve import TypedValve

__all__ = [
    "TypedFilter",
    "TypedTap",
    "TypedValve",
    "TypedHook",
    "TypedPipeline",
]
