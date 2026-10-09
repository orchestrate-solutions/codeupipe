"""TypedPipeline[Ctx] — orchestrator for typed payloads.

Same shape as ``Pipeline``: filters, taps, valves, hooks, and State.
Ctx flows through unchanged in type; only its data mutates
(depending on your Ctx implementation).

Two invariants preserved from the manifesto:
1. Removing every Tap yields identical output.
2. Same ctx through same pipeline yields same output.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Generic, List, Optional, TypeVar, Union

from ..state import State
from .filter import TypedFilter
from .hook import TypedHook
from .tap import TypedTap

Ctx = TypeVar("Ctx")

_FilterStep = ("filter", TypedFilter)  # type: ignore[misc]
_TapStep = ("tap", TypedTap)  # type: ignore[misc]


class TypedPipeline(Generic[Ctx]):
    """A pipeline over a typed context ``Ctx``."""

    def __init__(self) -> None:
        self._steps: List[tuple[str, Union[TypedFilter[Ctx], TypedTap[Ctx]], str]] = []
        self._hooks: List[TypedHook[Ctx]] = []
        self._state: State = State()
        self._observe_timing: bool = False
        self._observe_state: bool = True
        self._disabled_taps: set[str] = set()

    # ------------------------------------------------------------------
    # Builder API
    # ------------------------------------------------------------------

    def add_filter(
        self, filter_: TypedFilter[Ctx], name: Optional[str] = None
    ) -> "TypedPipeline[Ctx]":
        n = name or filter_.name
        self._steps.append((n, filter_, "filter"))
        return self

    def add_tap(self, tap: TypedTap[Ctx], name: Optional[str] = None) -> "TypedPipeline[Ctx]":
        n = name or tap.name
        self._steps.append((n, tap, "tap"))
        return self

    def use_hook(self, hook: TypedHook[Ctx]) -> "TypedPipeline[Ctx]":
        self._hooks.append(hook)
        return self

    def observe(self, timing: bool = False) -> "TypedPipeline[Ctx]":
        self._observe_timing = timing
        return self

    def observe_state(self, enabled: bool) -> "TypedPipeline[Ctx]":
        self._observe_state = enabled
        return self

    def disable_taps(self, *names: str) -> "TypedPipeline[Ctx]":
        for n in names:
            self._disabled_taps.add(n)
        return self

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def state(self) -> State:
        return self._state

    def step_count(self) -> int:
        return len(self._steps)

    def describe(self) -> List[tuple[str, str]]:
        return [(name, kind) for name, _step, kind in self._steps]

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _can_run_fast(self) -> bool:
        return (
            not self._hooks
            and not self._observe_timing
            and not self._disabled_taps
            and all(kind == "filter" for _, _, kind in self._steps)
        )

    def _run_fast(self, ctx: Ctx) -> Ctx:
        self._state = State()
        observe_state = self._observe_state
        for name, step, _kind in self._steps:
            ctx = step.call(ctx)  # type: ignore[union-attr]
            if observe_state:
                if getattr(step, "last_skipped", False):
                    self._state.mark_skipped(name)
                else:
                    self._state.mark_executed(name)
        return ctx

    def run(self, initial: Ctx) -> Ctx:
        """Execute the pipeline. Flows ctx through every step."""
        if self._can_run_fast():
            return self._run_fast(initial)

        self._state = State()
        ctx = initial

        for hook in self._hooks:
            hook.before(None, ctx)

        for name, step, kind in self._steps:
            t0 = time.perf_counter() if self._observe_timing else 0.0

            if kind == "tap":
                if name in self._disabled_taps:
                    if self._observe_state:
                        self._state.mark_skipped(name)
                    continue
                try:
                    step.observe(ctx)  # type: ignore[union-attr]
                except Exception:
                    # Taps swallow their own errors — manifesto invariant.
                    pass
                if self._observe_state:
                    self._state.mark_executed(name)
                continue

            # Filter
            for hook in self._hooks:
                hook.before(name, ctx)

            try:
                ctx = step.call(ctx)  # type: ignore[union-attr]
            except BaseException as e:
                for hook in self._hooks:
                    hook.on_error(name, e)
                raise

            if self._observe_state:
                # Valve skip detection
                last_skipped = getattr(step, "last_skipped", False)
                if last_skipped:
                    self._state.mark_skipped(name)
                else:
                    self._state.mark_executed(name)

            for hook in self._hooks:
                hook.after(name, ctx)

            if self._observe_timing:
                self._state.record_timing(name, time.perf_counter() - t0)

        for hook in self._hooks:
            hook.after(None, ctx)

        return ctx
