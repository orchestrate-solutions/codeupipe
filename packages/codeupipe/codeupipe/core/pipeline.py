"""
Pipeline: The Orchestrator

A Pipeline runs its steps in order. Filters change the Payload, Valves gate a
Filter, Taps observe, Hooks see the lifecycle, and State records what ran.
"""

import inspect
import time
from typing import Any, Dict, List, Optional, Tuple, TypeVar, Generic, Union
from .payload import Payload
from .filter import AsyncFilter, Filter
from .tap import AsyncTap, Tap
from .hook import Hook
from .state import State
from .step_label import label_of
from .async_step_in_sync_run import AsyncStepInSyncRun
from .valve import Valve

__all__ = ["Pipeline"]


TInput = TypeVar('TInput')
TOutput = TypeVar('TOutput')


# cup: allow-plain a primitive itself: the framework makes the primitives, so it is not written with them
class Pipeline(Generic[TInput, TOutput]):
    """
    Orchestrator — runs filters in sequence with hooks, taps, and state tracking.

    Build a pipeline by adding filters (.add_filter), taps (.add_tap),
    nested pipelines (.add_pipeline) and hooks (.use_hook). Run it with
    .run(payload), or .run_async(payload) when a step is async.
    After execution, inspect .state for execution metadata.
    """

    def __init__(self):
        self._preflight_key: Any = None
        self._preflight_cache: Any = None
        self._steps: List[Tuple[str, Any, str]] = []  # (label, step, type)
        # A step's label is its class name, with #n from the second use.
        self._uses: Dict[str, int] = {}
        self._hooks: List[Hook] = []
        self._state: State = State()
        self._observe_timing: bool = False
        self._observe_lineage: bool = False

    @property
    def state(self) -> State:
        """The State of the run that started last.

        A State belongs to one run. A caller with more than one run of this
        Pipeline at a time gives each run its own: ``run(payload, state)``.
        """
        return self._state

    @property
    def labels(self) -> List[str]:
        """Each step's label, in order."""
        return [label for label, _step, _type in self._steps]

    def _label(self, step: Any) -> str:
        """The step's class name, numbered from its second use in this pipeline."""
        base = label_of(step)
        count = self._uses.get(base, 0) + 1
        self._uses[base] = count
        self._preflight_key = None  # shape changed
        return base if count == 1 else f"{base}#{count}"

    @staticmethod
    def _require(step: Any, method: str, what: str) -> None:
        """Refuse a step that does not have the method of its kind."""
        if not callable(getattr(step, method, None)):
            raise TypeError(f"{what} has {method}(payload). {step!r} does not.")

    def add_filter(self, filter: Union[Filter[TInput, TOutput], AsyncFilter[TInput, TOutput]]) -> None:
        """Add a Filter. A filter whose ``call`` is a coroutine needs ``run_async()``."""
        if isinstance(filter, Valve):
            raise TypeError("A Valve is added with add_valve(predicate, filter), not with add_filter.")
        self._require(filter, "call", "A Filter")
        step_type = "async_filter" if self._is_async_method(filter, "call") else "filter"
        self._steps.append((self._label(filter), filter, step_type))

    def add_valve(self, predicate: Any, filter: Union[Filter[TInput, TOutput], AsyncFilter[TInput, TOutput]]) -> None:
        """Add a Valve: ``filter`` runs only when ``predicate.test(payload)`` is true.

        The condition comes first, then the Filter that it controls. When the
        test is false the Payload passes through unchanged and the step is
        recorded as skipped. The step has the label of its Filter.
        """
        if not callable(getattr(predicate, "test", None)) and callable(getattr(predicate, "call", None)) \
                and callable(getattr(filter, "test", None)):
            raise TypeError("The arguments are in the wrong order: add_valve(predicate, filter). "
                            "The condition comes first, then the Filter.")
        self._require(predicate, "test", "A Predicate")
        self._require(filter, "call", "A Filter")
        valve = Valve(filter, predicate)
        self._steps.append((self._label(valve), valve, "valve"))

    def add_tap(self, tap: Union[Tap, AsyncTap]) -> None:
        """Add a Tap. A tap whose ``observe`` is a coroutine needs ``run_async()``."""
        self._require(tap, "observe", "A Tap")
        step_type = "async_tap" if self._is_async_method(tap, "observe") else "tap"
        self._steps.append((self._label(tap), tap, step_type))

    def use_hook(self, hook: Hook) -> None:
        """Attach a lifecycle hook. A hook with coroutine methods needs ``run_async()``."""
        self._preflight_key = None  # shape changed
        self._hooks.append(hook)

    def add_pipeline(self, pipeline: 'Pipeline') -> None:
        """Nest a Pipeline as a single step inside this Pipeline."""
        if not isinstance(pipeline, Pipeline):
            raise TypeError(f"add_pipeline takes a Pipeline. {pipeline!r} is not one.")
        self._steps.append((self._label(pipeline), pipeline, "pipeline"))

    def observe(self, *, timing: bool = True, lineage: bool = False) -> None:
        """Enable observation features (timing, lineage tracking)."""
        self._observe_timing = timing
        self._observe_lineage = lineage

    @staticmethod
    def _is_async_method(obj: Any, method_name: str) -> bool:
        method = getattr(obj, method_name, None)
        return inspect.iscoroutinefunction(method)

    def _hooks_are_sync_only(self) -> bool:
        return all(
            not self._is_async_method(hook, "before")
            and not self._is_async_method(hook, "after")
            and not self._is_async_method(hook, "on_error")
            for hook in self._hooks
        )

    def _can_run_fast(self) -> bool:
        """Whether the common case can skip hooks and instrumentation."""
        return not self._hooks and not self._observe_timing and not self._observe_lineage

    async def _run_fast(self, initial_payload: Payload[TInput], state: State) -> Payload[TOutput]:
        """Hot path for simple pipelines: no hooks, no timing, no lineage."""
        payload = initial_payload.copy()  # the caller's Payload is not changed
        for name, step, step_type in self._steps:
            if step_type == "tap":
                self._observe(name, step, payload, state)
                state.mark_executed(name)
                continue

            if step_type == "async_tap":
                await self._observe_async(name, step, payload, state)
                state.mark_executed(name)
                continue

            if step_type == "pipeline":
                payload = await step.run_async(payload)
                state.mark_executed(name)
                continue

            if step_type == "valve":
                # The Pipeline asks the Predicate itself. A flag on the Valve
                # would be shared by each run that is in progress.
                if not step._predicate(payload):
                    state.mark_skipped(name)
                    continue
                result = step._inner.call(payload)
                payload = await result if inspect.isawaitable(result) else result
            elif step_type == "async_filter":
                payload = await step.call(payload)  # type: ignore[attr-defined]
            else:
                payload = step.call(payload)  # type: ignore[attr-defined]
            state.mark_executed(name)

        return payload  # type: ignore[return-value]

    @staticmethod
    def _stamp(payload: Any, label: str) -> None:
        """Lineage: record that a step ran. Payload keeps the label. A type of
        your own keeps it only if it has ``_stamp(label)``; for any other type,
        lineage does nothing. The return value of ``_stamp`` is not used."""
        stamp = getattr(payload, "_stamp", None)
        if stamp is not None:
            stamp(label)

    @staticmethod
    async def _invoke(fn, *args):
        """Call fn(*args), awaiting the result only if it is a coroutine."""
        result = fn(*args)
        if inspect.isawaitable(result):
            result = await result
        return result

    async def run_async(self, initial_payload: Payload[TInput], state: Optional[State] = None) -> Payload[TOutput]:
        """Execute with async steps allowed (opt-in). ``run()`` is the default.

        The run writes into ``state`` when the caller gives one, and into a
        new State when not. It is a local of this call, so two runs that are
        in progress at the same time never write into the same State.
        """
        if state is None:
            state = State()
        self._state = state  # the State of the run that started last
        if self._can_run_fast():
            return await self._run_fast(initial_payload, state)

        payload = initial_payload.copy()  # the caller's Payload is not changed
        _step_name: Optional[str] = None
        _step_t0: Optional[float] = None

        for hook in self._hooks:
            await self._invoke(hook.before, None, payload)

        _failing: Any = None  # the step running when an exception escapes
        try:
            for name, step, step_type in self._steps:
                _step_name = name
                _step_t0 = None
                _failing = None

                if step_type == "tap":
                    self._observe(name, step, payload, state)
                    state.mark_executed(name)
                    continue

                if step_type == "async_tap":
                    await self._observe_async(name, step, payload, state)
                    state.mark_executed(name)
                    continue

                _step_t0 = time.monotonic()
                _failing = name

                for hook in self._hooks:
                    await self._invoke(hook.before, name, payload)

                if step_type == "pipeline":
                    payload = await step.run_async(payload)
                    state.mark_executed(name)
                elif step_type == "valve":
                    if step._predicate(payload):
                        result = step._inner.call(payload)
                        payload = await result if inspect.isawaitable(result) else result
                        state.mark_executed(name)
                    else:
                        state.mark_skipped(name)
                else:
                    if step_type == "async_filter":
                        payload = await step.call(payload)  # type: ignore[attr-defined]
                    else:
                        payload = step.call(payload)  # type: ignore[attr-defined]
                    state.mark_executed(name)

                for hook in self._hooks:
                    await self._invoke(hook.after, name, payload)

                if self._observe_timing:
                    state.record_timing(name, time.monotonic() - _step_t0)
                if self._observe_lineage:
                    self._stamp(payload, name)

        except Exception as e:
            if _step_t0 is not None and _step_name is not None and self._observe_timing:
                state.record_timing(_step_name, time.monotonic() - _step_t0)
            if _failing is not None:
                # The failing step first, then the pipeline: on_error mirrors
                # before/after, which fire at both levels.
                for hook in self._hooks:
                    await self._invoke(hook.on_error, _failing, e, payload)
            for hook in self._hooks:
                await self._invoke(hook.on_error, None, e, payload)
            raise

        for hook in self._hooks:
            await self._invoke(hook.after, None, payload)

        return payload  # type: ignore

    def _observe(self, name: str, tap: Any, payload: Payload, state: State) -> None:
        """Run a sync Tap on Plane B: its failure never halts Plane A.

        The ``Exception`` is recorded in ``state.errors`` under the Tap's
        name, the payload continues, and ``on_error`` hooks are not fired
        (they govern Plane A). BaseExceptions such as KeyboardInterrupt still
        propagate.
        """
        try:
            tap.observe(payload)
        except Exception as error:
            state.record_error(name, error)

    async def _observe_async(self, name: str, tap: Any, payload: Payload, state: State) -> None:
        """``_observe`` for a Tap whose ``observe`` may be a coroutine."""
        try:
            result = tap.observe(payload)
            if inspect.isawaitable(result):
                await result
        except Exception as error:
            state.record_error(name, error)

    # ------------------------------------------------------------------
    # Sync execution: the default. Never starts an event loop.
    # ------------------------------------------------------------------

    def run(self, initial_payload: Payload[TInput], state: Optional[State] = None) -> Payload[TOutput]:
        """Execute synchronously (the default).

        The run writes into ``state`` when the caller gives one, and into a
        new State when not (see ``run_async``).

        Never starts an event loop: if the pipeline contains async work (an
        async filter, tap or hook) this raises ``AsyncStepInSyncRun``; use
        ``run_async()`` for those pipelines. Entering the async path costs
        about 125 µs per call, 9 to 25 times the pipeline itself.
        """
        offender = self._preflight()
        if offender is not None:
            raise AsyncStepInSyncRun(
                f"cannot run async step '{offender}' inside run(). Use "
                f"run_async() from async code, or replace it with a sync step."
            )
        return self._run_sync(initial_payload, state)

    def _preflight(self) -> Optional[str]:
        """The first async offender in this pipeline, or None. Cached.

        The answer depends only on the pipeline's shape, so it is computed
        once and recomputed when steps or hooks change, instead of scanning
        every step on every run(). Nested pipelines are asked each run
        through their own cache, so editing a child after nesting stays safe.
        """
        key = (len(self._steps), len(self._hooks))
        if self._preflight_key != key:
            self._preflight_cache = (self._first_async_offender(nested=False),
                                     [(n, s) for n, s, t in self._steps if t == "pipeline"])
            self._preflight_key = key
        offender, children = self._preflight_cache
        if offender is None:
            for name, child in children:
                inner = child._first_async_offender()
                if inner is not None:
                    return f"{name}.{inner}"
        return offender

    def _first_async_offender(self, nested: bool = True) -> Optional[str]:
        """Name of the first piece of async work, or None if fully sync."""
        for hook in self._hooks:
            if not self._hooks_are_sync_only():
                return f"hook {type(hook).__name__}"
        for name, step, step_type in self._steps:
            if step_type == "async_tap":
                return name
            if step_type == "async_filter" or (step_type == "valve" and not self._has_sync_path(step)):
                return name
            if step_type == "pipeline" and nested:
                inner = step._first_async_offender()
                if inner is not None:
                    return f"{name}.{inner}"
        return None

    def _has_sync_path(self, step: Any) -> bool:
        """True for an async-declared step that can run with no event loop.

        ``Valve.call`` is async because its inner filter *may* be. A Valve
        over a sync inner can run with no loop. A Valve over an async (or
        nested Valve) inner is async work.
        """
        if not callable(getattr(step, "call_sync", None)):
            return False
        inner = getattr(step, "_inner", None)
        return inner is None or not self._is_async_method(inner, "call")

    def _run_sync(self, initial_payload: Payload[TInput], state: Optional[State]) -> Payload[TOutput]:
        if state is None:
            state = State()
        self._state = state  # the State of the run that started last
        payload = initial_payload.copy()  # the caller's Payload is not changed

        # Clock reads cost ~0.1 µs each; only take them when someone reads them.
        timed = self._observe_timing
        hooks = self._hooks

        for hook in hooks:
            hook.before(None, payload)

        _step_name: Optional[str] = None
        _step_t0: Optional[float] = None
        _failing: Optional[str] = None  # the step running when an exception escapes

        try:
            for name, step, step_type in self._steps:
                _step_name = name
                _step_t0 = None
                _failing = None

                if step_type == "tap":
                    self._observe(name, step, payload, state)
                    state.mark_executed(name)
                    continue

                if timed:
                    _step_t0 = time.monotonic()
                _failing = name

                for hook in hooks:
                    hook.before(name, payload)
                if step_type == "pipeline":
                    payload = step.run(payload)
                    state.mark_executed(name)
                elif step_type == "valve":
                    # The Pipeline asks the Predicate itself: a flag on the
                    # Valve would be shared by each run that is in progress.
                    if step._predicate(payload):
                        payload = step._sync_inner(payload)  # admitted by _has_sync_path
                        state.mark_executed(name)
                    else:
                        state.mark_skipped(name)
                else:
                    payload = step.call(payload)  # type: ignore[attr-defined]
                    state.mark_executed(name)
                for hook in hooks:
                    hook.after(name, payload)

                if timed:
                    state.record_timing(name, time.monotonic() - _step_t0)
                if self._observe_lineage:
                    self._stamp(payload, name)

        except Exception as e:
            if timed and _step_t0 is not None and _step_name is not None:
                state.record_timing(_step_name, time.monotonic() - _step_t0)
            if _failing is not None:
                # The failing step first, then the pipeline: on_error mirrors
                # before/after, which fire at both levels.
                for hook in hooks:
                    hook.on_error(_failing, e, payload)
            for hook in hooks:
                hook.on_error(None, e, payload)
            raise

        for hook in hooks:
            hook.after(None, payload)
        return payload  # type: ignore[return-value]
