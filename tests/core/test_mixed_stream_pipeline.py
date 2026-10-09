"""Tests for mixing sync filters, async filters, stream filters, and taps in one pipeline."""

import asyncio

import pytest

from codeupipe import Payload, Pipeline, Valve


# ── Components ──────────────────────────────────────────────────────


class UpperCase:
    """Sync filter — uppercases the 'text' field."""

    def call(self, payload):
        return payload.insert("text", payload.get("text", "").upper())


class AddPrefix:
    """Async filter — prepends 'PREFIX_' to 'text'."""

    async def call(self, payload):
        return payload.insert("text", "PREFIX_" + payload.get("text", ""))


class Duplicate:
    """StreamFilter — fan-out: 1 chunk → 2 chunks (original + copy)."""

    async def stream(self, chunk):
        yield chunk
        yield chunk.insert("copy", True)


class DropShort:
    """StreamFilter — drop: filters out chunks where text < 5 chars."""

    async def stream(self, chunk):
        if len(chunk.get("text", "")) >= 5:
            yield chunk


class SyncLogger:
    """Sync tap — records observed text values."""

    def __init__(self):
        self.seen = []

    def observe(self, payload):
        self.seen.append(payload.get("text"))


class AsyncCounter:
    """Async tap — counts chunks observed."""

    def __init__(self):
        self.count = 0

    async def observe(self, payload):
        self.count += 1


class AppendSuffix:
    """Sync filter — appends '_DONE' to 'text'."""

    def call(self, payload):
        return payload.insert("text", payload.get("text", "") + "_DONE")


# ── Helpers ─────────────────────────────────────────────────────────


def run(coro):
    return asyncio.run(coro)


async def collect(pipeline, source):
    results = []
    async for chunk in pipeline.stream_async(source):
        results.append(chunk)
    return results


async def make_source(*texts):
    for t in texts:
        yield Payload({"text": t})


# ── Tests ───────────────────────────────────────────────────────────


class _Predicate:

    def test(self, p):
        return p.get('text', '') != 'skip'

class _Predicate2:

    def test(self, p):
        return len(p.get('text', '')) > 2


class TestMixedStreamPipeline:
    """All five component types in one pipeline.stream() call."""

    def test_sync_async_stream_taps_all_together(self):
        """sync filter → sync tap → stream filter (fan-out) → async filter → async tap"""
        logger = SyncLogger()
        counter = AsyncCounter()

        pipeline = Pipeline()
        pipeline.add_filter(UpperCase())
        pipeline.add_tap(logger)
        pipeline.add_filter(Duplicate())
        pipeline.add_filter(AddPrefix())
        pipeline.add_tap(counter)

        async def go():
            return await collect(pipeline, make_source("hello", "world", "test"))

        results = run(go())

        # 3 input × 2 fan-out = 6 output chunks
        assert len(results) == 6

        # Logger sees after UpperCase but before Duplicate (3 chunks)
        assert logger.seen == ["HELLO", "WORLD", "TEST"]

        # Counter sees after fan-out + prefix (6 chunks)
        assert counter.count == 6

        # All have prefix
        texts = [r.get("text") for r in results]
        assert texts == [
            "PREFIX_HELLO",
            "PREFIX_HELLO",
            "PREFIX_WORLD",
            "PREFIX_WORLD",
            "PREFIX_TEST",
            "PREFIX_TEST",
        ]

        # Odd-index results are copies
        assert results[0].get("copy") is None
        assert results[1].get("copy") is True
        assert results[2].get("copy") is None
        assert results[3].get("copy") is True

    def test_stream_filter_then_sync_filter(self):
        """stream filter (fan-out) → sync filter — verifies regular filters process expanded chunks."""
        pipeline = Pipeline()
        pipeline.add_filter(Duplicate())
        pipeline.add_filter(AppendSuffix())

        async def go():
            return await collect(pipeline, make_source("a", "b"))

        results = run(go())

        assert len(results) == 4
        texts = [r.get("text") for r in results]
        assert texts == ["a_DONE", "a_DONE", "b_DONE", "b_DONE"]

    def test_sync_filter_then_stream_filter_drop(self):
        """sync filter → stream filter (drop) — short entries are removed."""
        pipeline = Pipeline()
        pipeline.add_filter(UpperCase())
        pipeline.add_filter(DropShort())

        async def go():
            return await collect(pipeline, make_source("hi", "hello", "no", "streaming"))

        results = run(go())

        # 'hi'→'HI' (2 chars, dropped), 'hello'→'HELLO' (5, kept),
        # 'no'→'NO' (2, dropped), 'streaming'→'STREAMING' (9, kept)
        texts = [r.get("text") for r in results]
        assert texts == ["HELLO", "STREAMING"]

    def test_two_stream_filters_chained(self):
        """stream filter (fan-out) → stream filter (drop) — fan-out then filter."""
        pipeline = Pipeline()
        pipeline.add_filter(Duplicate())        # 1→2
        pipeline.add_filter(DropShort())  # drop short ones

        async def go():
            return await collect(pipeline, make_source("hello", "hi"))

        results = run(go())

        # 'hello' → 2 chunks both 'hello' (5 chars, both kept)
        # 'hi' → 2 chunks both 'hi' (2 chars, both dropped)
        texts = [r.get("text") for r in results]
        assert texts == ["hello", "hello"]

    def test_valve_in_streaming_mode(self):
        """valve (conditional) in a stream pipeline."""
        pipeline = Pipeline()
        pipeline.add_filter(Valve(UpperCase(), _Predicate()))

        async def go():
            return await collect(pipeline, make_source("hello", "skip", "world"))

        results = run(go())

        texts = [r.get("text") for r in results]
        # 'hello' → uppercased, 'skip' → passed through unchanged, 'world' → uppercased
        assert texts == ["HELLO", "skip", "WORLD"]

    def test_all_five_types_with_valve(self):
        """sync filter + async filter + stream filter + valve + sync tap + async tap."""
        logger = SyncLogger()
        counter = AsyncCounter()

        pipeline = Pipeline()
        pipeline.add_filter(UpperCase())                      # sync
        pipeline.add_tap(logger)                              # sync tap
        pipeline.add_filter(Valve(AddPrefix(), _Predicate2()))                                                               # valve + async inner
        pipeline.add_filter(Duplicate())                         # stream
        pipeline.add_tap(counter)                            # async tap

        async def go():
            return await collect(pipeline, make_source("hi", "hello"))

        results = run(go())

        # 'hi' → 'HI' (2 chars) → valve skips prefix → dup → 'HI', 'HI'
        # 'hello' → 'HELLO' (5 chars) → valve passes → 'PREFIX_HELLO' → dup → 2 copies
        assert len(results) == 4

        texts = [r.get("text") for r in results]
        assert texts == ["HI", "HI", "PREFIX_HELLO", "PREFIX_HELLO"]

        # Logger saw 2 chunks (before valve)
        assert logger.seen == ["HI", "HELLO"]
        # Counter saw 4 chunks (after fan-out)
        assert counter.count == 4

    def test_empty_source_with_mixed_pipeline(self):
        """Empty source through a mixed pipeline produces zero output."""
        pipeline = Pipeline()
        pipeline.add_filter(UpperCase())
        pipeline.add_filter(Duplicate())
        pipeline.add_filter(AddPrefix())

        async def go():
            return await collect(pipeline, make_source())

        results = run(go())
        assert results == []

    def test_state_tracks_all_step_types(self):
        """Pipeline state tracks execution of all mixed step types."""
        logger = SyncLogger()
        counter = AsyncCounter()

        pipeline = Pipeline()
        pipeline.add_filter(UpperCase())
        pipeline.add_tap(logger)
        pipeline.add_filter(Duplicate())
        pipeline.add_filter(AddPrefix())
        pipeline.add_tap(counter)

        async def go():
            return await collect(pipeline, make_source("a"))

        run(go())

        for step in ("UpperCase", "SyncLogger", "Duplicate", "AddPrefix", "AsyncCounter"):
            assert f"{__name__}.{step}" in pipeline.state.executed
