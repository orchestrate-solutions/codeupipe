"""Valve.call_sync — a synchronous path for synchronous inner filters.

`Valve.call` is async because the inner filter *may* be. Pipeline therefore
classified every Valve as an async step and paid `asyncio.run` per invocation:

    plain filter step     1.03 µs
    valve step          119.31 µs      <-- 116x

That is the dominant cost in any valve-heavy synchronous pipeline, where
every gated step is a Valve.

`call_sync` runs a sync inner filter directly. An async inner still resolves
correctly, at the same cost as before, so nothing regresses.
"""

import asyncio

import pytest

from codeupipe import Payload
from codeupipe.core.valve import Valve
from codeupipe import Pipeline


class Append:
    """Synchronous inner filter."""

    def call(self, payload):
        return payload.insert("s", payload.get("s") + "!")


class AsyncAppend:
    """Async inner filter — must still work through the sync path."""

    async def call(self, payload):
        return payload.insert("s", payload.get("s") + "?")


class _Predicate:

    def test(self, p):
        return True

class _Predicate2:

    def test(self, p):
        return False

class _Predicate3:

    def test(self, p):
        return False

class _Predicate4:

    def test(self, p):
        return True

class _Predicate5:

    def test(self, p):
        return True

class _Yes:

    def test(self, p):
        return True

class _No:

    def test(self, p):
        return False


class TestCallSyncSemantics:
    def test_runs_inner_when_predicate_passes(self):
        valve = Valve(Append(), _Predicate())
        assert valve.call_sync(Payload({"s": "a"})).get("s") == "a!"

    def test_passes_through_when_predicate_fails(self):
        valve = Valve(Append(), _Predicate2())
        payload = Payload({"s": "a"})
        assert valve.call_sync(payload) is payload

    def test_matches_the_async_path_exactly(self):
        for verdict in (_Yes(), _No()):
            valve = Valve(Append(), verdict)
            sync_result = valve.call_sync(Payload({"s": "a"}))
            async_result = asyncio.run(Valve(Append(), verdict)
                                       .call(Payload({"s": "a"})))
            assert sync_result.to_dict() == async_result.to_dict()

    def test_skip_flag_is_recorded(self):
        valve = Valve(Append(), _Predicate3())
        valve.call_sync(Payload({"s": "a"}))
        assert valve._last_skipped is True

    def test_executed_flag_is_recorded(self):
        valve = Valve(Append(), _Predicate4())
        valve.call_sync(Payload({"s": "a"}))
        assert valve._last_skipped is False

    def test_async_inner_still_resolves(self):
        # No regression: an async inner costs what it always did.
        valve = Valve(AsyncAppend(), _Predicate5())
        assert valve.call_sync(Payload({"s": "a"})).get("s") == "a?"


class _Predicate7:

    def test(self, p):
        return True

class _Predicate8:

    def test(self, p):
        return False

class _Predicate9:

    def test(self, p):
        return True


class TestThroughSyncPipeline:
    def test_valve_runs_in_sync_pipeline(self):
        pipeline = Pipeline()
        pipeline.add_valve(_Predicate7(), Append())
        assert pipeline.run(Payload({"s": "a"})).get("s") == "a!"

    def test_skipped_valve_is_marked_skipped(self):
        pipeline = Pipeline()
        pipeline.add_valve(_Predicate8(), Append())
        pipeline.run(Payload({"s": "a"}))
        assert "Append" in pipeline.state.skipped

    def test_valve_is_no_longer_far_slower_than_a_plain_step(self):
        """The regression guard. Not a benchmark — an order-of-magnitude
        sanity check that the asyncio path is not back."""
        import timeit
        plain = Pipeline(); plain.add_filter(Append())
        valved = Pipeline(); valved.add_valve(_Predicate9(), Append())
        n = 300
        t_plain = timeit.timeit(lambda: plain.run(Payload({"s": "a"})), number=n)
        t_valve = timeit.timeit(lambda: valved.run(Payload({"s": "a"})), number=n)
        assert t_valve < t_plain * 10, (
            f"valve is {t_valve / t_plain:.0f}x a plain step — asyncio path is back"
        )
