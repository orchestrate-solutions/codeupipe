"""TypedHook — lifecycle callback for the typed pipeline.

Fires on before/after for each step and the pipeline itself, and on
error at any step. ``step_name`` is None for pipeline-level events.

Note on on_error: it receives ``err`` only, not ctx. If you need
ctx-on-error, place a TypedTap immediately upstream and snapshot ctx
there. Hooks are lifecycle, not state.
"""

from __future__ import annotations

from typing import Generic, Optional, TypeVar

Ctx = TypeVar("Ctx")


class TypedHook(Generic[Ctx]):
    """Lifecycle callback attached to a TypedPipeline."""

    def before(self, step_name: Optional[str], ctx: Ctx) -> None:
        return None

    def after(self, step_name: Optional[str], ctx: Ctx) -> None:
        return None

    def on_error(self, step_name: Optional[str], err: BaseException) -> None:
        return None
