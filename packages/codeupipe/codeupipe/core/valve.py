"""
Valve: Conditional Flow Control

A Valve holds a Filter and a predicate. The Filter runs only when the
predicate is true; otherwise the payload passes through unchanged.
``Pipeline.add_valve(predicate, filter)`` makes one. It is not a public name.

Two entry points (deliberate)
-----------------------------

``call`` is async; ``call_sync`` is not. Both honour the same contract — same
predicate, same skip semantics, same result.

``call`` has to be async because the *inner* filter may be, and a Valve cannot
know which until it holds one. That declaration is what the Pipeline reads to
classify a step, so before ``call_sync`` existed every Valve was treated as an
async step and paid ``asyncio.run`` on each invocation — an event loop spun up
per valve, per call:

    plain filter step     1.03 µs
    valve step          119.31 µs      116x
    valve step (fixed)    1.41 µs      1.4x

That cost was invisible in async pipelines, where the loop already exists, and
crushing in synchronous valve-heavy ones, such as generated pipelines that
gate nearly every step with a Valve.

``call_sync`` runs a synchronous inner directly. An async inner is still
resolved, at exactly the cost it had before — so the fast path is an addition,
never a behaviour change. Keep both in step: a change to one is a change to the
Valve contract and belongs in the other.
"""

import inspect
from typing import Callable, Generic, TypeVar
from .payload import Payload
from .filter import Filter
from .predicate import Predicate

__all__ = ["Valve"]

TInput = TypeVar('TInput')
TOutput = TypeVar('TOutput')


class Valve(Generic[TInput, TOutput]):
    """
    Conditional flow control — gates a Filter with a predicate.

    If the predicate returns True, the inner filter processes the payload.
    If False, the payload passes through unchanged.

    Conforms to the Filter protocol so it can be used anywhere a Filter is expected.
    """

    def __init__(
        self,
        inner: Filter[TInput, TOutput],
        predicate: "Predicate",
    ):
        # The predicate is an object with test(payload) -> bool. Its settings
        # are on the instance.
        self._inner = inner
        self._predicate_object = predicate
        self._predicate = predicate.test  # bound once: called per run
        # Resolved once: call_sync runs per step per run, so it should not
        # look the inner filter's entry point up every time.
        inner_sync = getattr(inner, "call_sync", None)
        self._inner_sync_call = inner_sync if callable(inner_sync) else None
        self._inner_is_sync = self._inner_sync_call is not None or not inspect.iscoroutinefunction(
            getattr(inner, "call", None))
        # What a synchronous run calls when the Predicate holds. The Pipeline
        # asks the Predicate and calls this itself, and reads no flag from
        # the Valve: a flag would be shared by each run that is in progress.
        self._sync_inner = self._inner_sync_call if self._inner_sync_call is not None else inner.call

    async def call(self, payload: Payload[TInput]) -> Payload[TOutput]:
        """Execute the inner filter only if the predicate passes."""
        if self._predicate(payload):
            self._last_skipped = False
            result = self._inner.call(payload)
            if inspect.isawaitable(result):
                result = await result
            return result
        self._last_skipped = True
        return payload  # type: ignore — pass through unchanged

    def call_sync(self, payload: Payload[TInput]) -> Payload[TOutput]:
        """Same contract as ``call``, without requiring an event loop.

        ``call`` is async because the *inner* filter may be, which made
        the Pipeline classify every Valve as an async step and pay
        ``asyncio.run`` on each invocation — 119 µs against 1.03 µs for a
        plain step, 116x. In a valve-heavy synchronous pipeline that dominates
        everything else.

        A synchronous inner runs directly here. An async inner is still
        resolved, at exactly the cost it had before, so nothing regresses.
        """
        if not self._predicate(payload):
            self._last_skipped = True
            return payload  # type: ignore — pass through unchanged

        self._last_skipped = False
        if self._inner_sync_call is not None:
            return self._inner_sync_call(payload)
        result = self._inner.call(payload)
        if not self._inner_is_sync and inspect.isawaitable(result):
            import asyncio

            result = asyncio.run(result)
        return result

    def __repr__(self) -> str:
        return f"Valve({type(self._predicate_object).__name__}, {type(self._inner).__name__})"
