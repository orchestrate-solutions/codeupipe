"""
Tests for streaming support in codeupipe.

Covers:
- Regular (batch) Filter auto-adapted for streaming
- StreamFilter protocol (yield 0, 1, or N chunks)
- Valve per-chunk gating in stream mode
- Tap per-chunk observation in stream mode
- Hook lifecycle (once per filter, not per chunk)
- State.chunks_processed tracking
- Mixed sync/async in stream mode
- Error propagation mid-stream
"""

import asyncio
from typing import AsyncIterator
import pytest
from codeupipe import Payload, Pipeline, Valve, Hook, StreamFilter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(coro):
    return asyncio.run(coro)


async def collect(aiter):
    """Drain an async iterator into a list."""
    results = []
    async for item in aiter:
        results.append(item)
    return results


async def make_source(*dicts):
    """Create an async generator from dicts."""
    for d in dicts:
        yield Payload(d)


# ===========================================================================
# Basic streaming with regular Filters
# ===========================================================================

class DoubleFilter:

    def call(self, payload: Payload) -> Payload:
        return payload.insert('n', payload.get('n', 0) * 2)

class AddOne:

    def call(self, payload: Payload) -> Payload:
        return payload.insert('n', payload.get('n', 0) + 1)

class Square:

    async def call(self, payload: Payload) -> Payload:
        return payload.insert('n', payload.get('n', 0) ** 2)

class PassFilter:

    def call(self, payload: Payload) -> Payload:
        return payload


class TestStreamWithBatchFilter:
    def test_single_filter_transforms_each_chunk(self):

        async def go():
            pipeline = Pipeline()
            pipeline.add_filter(DoubleFilter())
            return await collect(pipeline.stream_async(
                make_source({"n": 1}, {"n": 2}, {"n": 3})
            ))

        results = run(go())
        assert [r.get("n") for r in results] == [2, 4, 6]

    def test_chained_filters_process_each_chunk(self):


        async def go():
            pipeline = Pipeline()
            pipeline.add_filter(AddOne())
            pipeline.add_filter(Square())
            return await collect(pipeline.stream_async(
                make_source({"n": 1}, {"n": 2}, {"n": 3})
            ))

        results = run(go())
        # (1+1)^2=4, (2+1)^2=9, (3+1)^2=16
        assert [r.get("n") for r in results] == [4, 9, 16]

    def test_empty_source_yields_nothing(self):

        async def go():
            pipeline = Pipeline()
            pipeline.add_filter(PassFilter())
            return await collect(pipeline.stream_async(make_source()))

        assert run(go()) == []


# ===========================================================================
# StreamFilter protocol — fan-out, filtering, pass-through
# ===========================================================================

class DropOdd:

    async def stream(self, chunk: Payload) -> AsyncIterator[Payload]:
        if chunk.get('n', 0) % 2 == 0:
            yield chunk

class SplitFilter:

    async def stream(self, chunk: Payload) -> AsyncIterator[Payload]:
        text = chunk.get('text', '')
        for word in text.split():
            yield Payload({'word': word})

class UpperStream:

    async def stream(self, chunk: Payload) -> AsyncIterator[Payload]:
        yield chunk.insert('name', chunk.get('name', '').upper())

class AddPrefix:

    def call(self, payload: Payload) -> Payload:
        return payload.insert('line', '>> ' + payload.get('line', ''))

class DropEmpty:

    async def stream(self, chunk: Payload) -> AsyncIterator[Payload]:
        if chunk.get('line', '').strip():
            yield chunk


class TestStreamFilter:
    def test_stream_filter_can_drop_chunks(self):
        """Yield nothing → chunk is filtered out."""

        async def go():
            pipeline = Pipeline()
            pipeline.add_filter(DropOdd())
            return await collect(pipeline.stream_async(
                make_source({"n": 1}, {"n": 2}, {"n": 3}, {"n": 4})
            ))

        results = run(go())
        assert [r.get("n") for r in results] == [2, 4]

    def test_stream_filter_fan_out(self):
        """Yield multiple chunks from one input."""

        async def go():
            pipeline = Pipeline()
            pipeline.add_filter(SplitFilter())
            return await collect(pipeline.stream_async(
                make_source({"text": "hello world"}, {"text": "foo bar baz"})
            ))

        results = run(go())
        assert [r.get("word") for r in results] == ["hello", "world", "foo", "bar", "baz"]

    def test_stream_filter_one_to_one(self):
        """Yield exactly one chunk — acts like a regular filter."""

        async def go():
            pipeline = Pipeline()
            pipeline.add_filter(UpperStream())
            return await collect(pipeline.stream_async(
                make_source({"name": "alice"}, {"name": "bob"})
            ))

        results = run(go())
        assert [r.get("name") for r in results] == ["ALICE", "BOB"]

    def test_stream_filter_after_batch_filter(self):
        """StreamFilter and batch Filter coexist in one pipeline."""


        async def go():
            pipeline = Pipeline()
            pipeline.add_filter(DropEmpty())
            pipeline.add_filter(AddPrefix())
            return await collect(pipeline.stream_async(
                make_source({"line": "hello"}, {"line": ""}, {"line": "world"})
            ))

        results = run(go())
        assert [r.get("line") for r in results] == [">> hello", ">> world"]


# ===========================================================================
# Valve in stream mode — per-chunk predicate
# ===========================================================================

class DiscountFilter:

    def call(self, payload: Payload) -> Payload:
        return payload.insert('price', payload.get('price', 0) * 0.9)


class _IsVip:

    def test(self, payload):
        return payload.get('vip') is True


class TestStreamValve:
    def test_valve_gates_per_chunk(self):

        valve = Valve(inner=DiscountFilter(), predicate=_IsVip())

        async def go():
            pipeline = Pipeline()
            pipeline.add_filter(valve)
            return await collect(pipeline.stream_async(
                make_source(
                    {"vip": True, "price": 100},
                    {"vip": False, "price": 200},
                    {"vip": True, "price": 50},
                )
            ))

        results = run(go())
        assert [r.get("price") for r in results] == [90.0, 200, 45.0]


# ===========================================================================
# Tap in stream mode — observe each chunk
# ===========================================================================

class CollectorTap:

    def __init__(self):
        self.seen = []

    async def observe(self, payload: Payload) -> None:
        self.seen.append(payload.get('n'))


class SyncCollectX:
    def __init__(self):
        self.seen = []

    def observe(self, payload: Payload) -> None:
        self.seen.append(payload.get("x"))


class TestStreamTap:
    def test_tap_observes_every_chunk(self):

        async def go():
            tap = CollectorTap()
            pipeline = Pipeline()
            pipeline.add_tap(tap)
            results = await collect(pipeline.stream_async(
                make_source({"n": 1}, {"n": 2}, {"n": 3})
            ))
            return results, tap

        results, tap = run(go())
        assert tap.seen == [1, 2, 3]
        assert [r.get("n") for r in results] == [1, 2, 3]

    def test_sync_tap_in_stream(self):
        tap = SyncCollectX()

        async def go():
            pipeline = Pipeline()
            pipeline.add_tap(tap)
            return await collect(pipeline.stream_async(
                make_source({"x": "a"}, {"x": "b"})
            ))

        run(go())
        assert tap.seen == ["a", "b"]


# ===========================================================================
# Hook lifecycle in stream mode
# ===========================================================================

class PassFilter2:

    def call(self, payload: Payload) -> Payload:
        return payload


class TestStreamHook:
    def test_hook_fires_once_per_filter_not_per_chunk(self):
        log = []

        class TrackHook(Hook):
            async def before(self, step, payload) -> None:
                log.append(f"before:{step or 'pipeline'}")

            async def after(self, step, payload) -> None:
                log.append(f"after:{step or 'pipeline'}")


        async def go():
            pipeline = Pipeline()
            pipeline.use_hook(TrackHook())
            pipeline.add_filter(PassFilter2())
            return await collect(pipeline.stream_async(
                make_source({"n": 1}, {"n": 2}, {"n": 3})
            ))

        run(go())
        # Hook fires: pipeline-before, filter-before, filter-after, pipeline-after
        # NOT once per chunk
        assert log.count(f"before:{__name__}.PassFilter2") == 1
        assert log.count(f"after:{__name__}.PassFilter2") == 1
        assert log.count("before:pipeline") == 1
        assert log.count("after:pipeline") == 1


# ===========================================================================
# State.chunks_processed tracking
# ===========================================================================

class AddOne2:

    def call(self, payload: Payload) -> Payload:
        return payload.insert('n', payload.get('n', 0) + 1)

class Duplicate:

    async def stream(self, chunk: Payload) -> AsyncIterator[Payload]:
        yield chunk
        yield chunk

class DropAll:

    async def stream(self, chunk: Payload) -> AsyncIterator[Payload]:
        return
        yield

class NopTap:

    async def observe(self, payload: Payload) -> None:
        pass


class TestStreamState:
    def test_chunks_processed_tracked_per_step(self):

        async def go():
            pipeline = Pipeline()
            pipeline.add_filter(AddOne2())
            _ = await collect(pipeline.stream_async(
                make_source({"n": 1}, {"n": 2}, {"n": 3}, {"n": 4})
            ))
            return pipeline.state

        state = run(go())
        assert state.chunks_processed[f"{__name__}.AddOne2"] == 4

    def test_stream_filter_fan_out_counts_outputs(self):

        async def go():
            pipeline = Pipeline()
            pipeline.add_filter(Duplicate())
            results = await collect(pipeline.stream_async(
                make_source({"a": 1}, {"a": 2})
            ))
            return results, pipeline.state

        results, state = run(go())
        assert len(results) == 4
        assert state.chunks_processed[f"{__name__}.Duplicate"] == 4  # 2 inputs × 2 outputs each

    def test_stream_filter_dropping_counts_only_emitted(self):

        async def go():
            pipeline = Pipeline()
            pipeline.add_filter(DropAll())
            results = await collect(pipeline.stream_async(
                make_source({"a": 1}, {"a": 2}, {"a": 3})
            ))
            return results, pipeline.state

        results, state = run(go())
        assert len(results) == 0
        assert state.chunks_processed.get(f"{__name__}.DropAll", 0) == 0

    def test_tap_chunks_tracked(self):

        async def go():
            pipeline = Pipeline()
            pipeline.add_tap(NopTap())
            _ = await collect(pipeline.stream_async(
                make_source({"x": 1}, {"x": 2})
            ))
            return pipeline.state

        state = run(go())
        assert state.chunks_processed[f"{__name__}.NopTap"] == 2

    def test_state_reset_clears_chunks(self):
        from codeupipe import State
        s = State()
        s.increment_chunks("a", 5)
        s.increment_chunks("b", 3)
        s.reset()
        assert s.chunks_processed == {}


# ===========================================================================
# Error propagation
# ===========================================================================

class BoomOnThree:

    def call(self, payload: Payload) -> Payload:
        if payload.get('n') == 3:
            raise ValueError('boom at 3')
        return payload

class BoomFilter:

    def call(self, payload: Payload) -> Payload:
        raise RuntimeError('stream fail')


class TestStreamErrors:
    def test_error_mid_stream_propagates(self):

        async def go():
            pipeline = Pipeline()
            pipeline.add_filter(BoomOnThree())
            return await collect(pipeline.stream_async(
                make_source({"n": 1}, {"n": 2}, {"n": 3}, {"n": 4})
            ))

        with pytest.raises(ValueError, match="boom at 3"):
            run(go())

    def test_error_hook_called_on_stream_failure(self):
        errors = []

        class ErrHook(Hook):
            async def on_error(self, filter, error, payload) -> None:
                errors.append(str(error))


        async def go():
            pipeline = Pipeline()
            pipeline.use_hook(ErrHook())
            pipeline.add_filter(BoomFilter())
            return await collect(pipeline.stream_async(make_source({"x": 1})))

        with pytest.raises(RuntimeError):
            run(go())

        assert "stream fail" in errors[0]
