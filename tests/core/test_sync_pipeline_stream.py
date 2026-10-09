"""Pipeline.stream — the synchronous streaming path.

CUP could express an async stream and had no synchronous equivalent. That is
an expressiveness gap rather than a missing convenience: a plain Python
generator is consumed with `for x in gen()`, and no CUP shape preserved that
contract. Routing it through the async path changes the caller to `async
for`; collecting into a list breaks laziness, early termination, and infinite
sources.
"""

from __future__ import annotations

import pytest

from codeupipe import Payload, Pipeline


class Double:
    def call(self, payload):
        return payload.insert("v", payload.get("v") * 2)


class FanOut:
    """1 chunk in -> N chunks out."""

    def __init__(self, times=3):
        self.times = times

    def stream(self, chunk):
        for i in range(self.times):
            yield chunk.insert("copy", i)


class Drop:
    """1 chunk in -> 0 chunks out."""

    def stream(self, chunk):
        return iter(())


class Collector:
    def __init__(self):
        self.seen = []

    def observe(self, payload):
        self.seen.append(payload.get("v"))


def source(*values):
    for v in values:
        yield Payload({"v": v})


class TestBasics:
    def test_regular_filter_is_adapted_one_to_one(self):
        pipeline = Pipeline()
        pipeline.add_filter(Double())
        assert [p.get("v") for p in pipeline.stream(source(1, 2, 3))] == [2, 4, 6]

    def test_stream_filter_fans_out(self):
        pipeline = Pipeline()
        pipeline.add_filter(FanOut(3))
        assert len(list(pipeline.stream(source(1, 2)))) == 6

    def test_stream_filter_can_drop(self):
        pipeline = Pipeline()
        pipeline.add_filter(Drop())
        assert list(pipeline.stream(source(1, 2, 3))) == []

    def test_steps_compose_in_order(self):
        pipeline = Pipeline()
        pipeline.add_filter(Double())
        pipeline.add_filter(FanOut(2))
        out = [p.get("v") for p in pipeline.stream(source(1))]
        assert out == [2, 2]

    def test_no_event_loop_is_required(self):
        """The whole point. `Pipeline.stream` is a coroutine; this is not."""
        import asyncio

        pipeline = Pipeline()
        pipeline.add_filter(Double())
        results = list(pipeline.stream(source(1)))
        assert results[0].get("v") == 2
        with pytest.raises(RuntimeError):
            asyncio.get_running_loop()


class TestLaziness:
    """Laziness is not an optimisation here — it is the contract.

    A generator that is collected into a list has different semantics from
    one that is streamed: infinite sources hang, early termination stops
    being possible, and side effects all happen up front.
    """

    def test_an_infinite_source_streams(self):
        def forever():
            value = 0
            while True:
                value += 1
                yield Payload({"v": value})

        pipeline = Pipeline()
        pipeline.add_filter(Double())
        out = []
        for payload in pipeline.stream(forever()):
            out.append(payload.get("v"))
            if len(out) == 4:
                break
        assert out == [2, 4, 6, 8]

    def test_upstream_is_not_consumed_beyond_demand(self):
        pulled = []

        def counted():
            for v in range(100):
                pulled.append(v)
                yield Payload({"v": v})

        pipeline = Pipeline()
        pipeline.add_filter(Double())
        stream = pipeline.stream(counted())
        next(stream)
        next(stream)
        # Two pulled, not a hundred. If this ever reads 100 the chain has
        # started materialising and every laziness guarantee above is void.
        assert len(pulled) == 2


class TestTaps:
    def test_a_tap_observes_every_chunk_and_passes_it_through(self):
        collector = Collector()
        pipeline = Pipeline()
        pipeline.add_filter(Double())
        pipeline.add_tap(collector)
        out = [p.get("v") for p in pipeline.stream(source(1, 2))]
        assert out == [2, 4]
        assert collector.seen == [2, 4]

    def test_removing_a_tap_does_not_change_output(self):
        """A framework invariant: Taps observe, they never alter the result."""
        def run(with_tap):
            pipeline = Pipeline()
            pipeline.add_filter(Double())
            if with_tap:
                pipeline.add_tap(Collector())
            return [p.get("v") for p in pipeline.stream(source(1, 2, 3))]

        assert run(with_tap=True) == run(with_tap=False)



class _Predicate:

    def test(self, p):
        return p.get('v') % 2 == 0


class TestValves:
    def test_a_valve_gates_per_chunk(self):
        from codeupipe.core.valve import Valve

        pipeline = Pipeline()
        pipeline.add_filter(Valve(Double(), _Predicate()))
        # Odd values pass through untouched; even ones are doubled.
        assert [p.get("v") for p in pipeline.stream(source(1, 2, 3, 4))] == [1, 4, 3, 8]


class TestState:
    def test_chunks_are_counted_per_step(self):
        pipeline = Pipeline()
        pipeline.add_filter(Double())
        list(pipeline.stream(source(1, 2, 3)))
        assert f"{__name__}.Double" in pipeline.state.executed
