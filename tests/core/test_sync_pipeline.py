"""
Tests for Pipeline — the zero-asyncio pipeline orchestrator.

Pipeline runs filters via call_sync() (or sync call()) sequentially
with no event loop, no thread pool, and no scheduling uncertainty.

RED PHASE: These tests define the contract before implementation.
"""

import inspect
import os
import sys
import time

import pytest

from codeupipe import Payload, State
from codeupipe.core.hook import Hook
from codeupipe import Pipeline


# ── Test Filters (sync) ─────────────────────────────────────────────


class AddOneFilter:
    """Sync filter — adds 1 to 'x'."""

    def call(self, payload: Payload) -> Payload:
        return payload.insert("x", payload.get("x") + 1)


class UpperFilter:
    """Sync filter — uppercases 'name'."""

    def call(self, payload: Payload) -> Payload:
        return payload.insert("name", payload.get("name").upper())


class BoomFilter:
    """Always raises."""

    def call(self, payload: Payload) -> Payload:
        raise ValueError("boom")


# ── Test Taps (sync) ────────────────────────────────────────────────


class RecordTap:
    """Sync tap that records observed payloads."""

    def __init__(self):
        self.seen = []

    def observe(self, payload: Payload) -> None:
        self.seen.append(payload.to_dict())


# ── Test Hooks (sync) ───────────────────────────────────────────────


class RecordHook:
    """Sync hook that records before/after/on_error calls."""

    def __init__(self):
        self.events = []

    def before(self, filter, payload):
        self.events.append(("before", filter, payload))

    def after(self, filter, payload):
        self.events.append(("after", filter, payload))

    def on_error(self, filter, error, payload):
        self.events.append(("on_error", filter, error, payload))


# ── Basic execution ─────────────────────────────────────────────────


class TestSyncPipelineBasic:
    """Pipeline runs sync filters with no asyncio."""

    def test_single_filter(self):
        sp = Pipeline()
        sp.add_filter(AddOneFilter())
        result = sp.run(Payload({"x": 10}))
        assert result.get("x") == 11

    def test_multiple_filters_sequential(self):
        sp = Pipeline()
        sp.add_filter(AddOneFilter())
        sp.add_filter(AddOneFilter())
        sp.add_filter(AddOneFilter())
        result = sp.run(Payload({"x": 0}))
        assert result.get("x") == 3

    def test_state_tracks_execution(self):
        sp = Pipeline()
        sp.add_filter(AddOneFilter())
        sp.add_filter(UpperFilter())
        sp.run(Payload({"x": 1, "name": "alice"}))
        assert sp.state.executed == ["AddOneFilter", "UpperFilter"]

    def test_returns_payload_type(self):
        sp = Pipeline()
        sp.add_filter(AddOneFilter())
        result = sp.run(Payload({"x": 0}))
        assert isinstance(result, Payload)
        assert result.get("x") == 1


# ── Taps ────────────────────────────────────────────────────────────


class TestSyncPipelineTaps:
    """Taps observe payloads without modifying them."""

    def test_tap_observes(self):
        tap = RecordTap()
        sp = Pipeline()
        sp.add_filter(AddOneFilter())
        sp.add_tap(tap)
        sp.run(Payload({"x": 5}))
        assert len(tap.seen) == 1
        assert tap.seen[0]["x"] == 6  # tap sees post-add payload

    def test_tap_state_tracked(self):
        sp = Pipeline()
        sp.add_tap(RecordTap())
        sp.run(Payload({"x": 1}))
        assert "RecordTap" in sp.state.executed


# ── Hooks ───────────────────────────────────────────────────────────


class TestSyncPipelineHooks:
    """Lifecycle hooks fire in sync mode."""

    def test_before_after_fire(self):
        hook = RecordHook()
        sp = Pipeline()
        sp.add_filter(AddOneFilter())
        sp.use_hook(hook)
        sp.run(Payload({"x": 0}))
        kinds = [e[0] for e in hook.events]
        # pipeline-start before, filter before, filter after, pipeline-end after
        assert kinds.count("before") >= 2
        assert kinds.count("after") >= 2

    def test_on_error_fires(self):
        hook = RecordHook()
        sp = Pipeline()
        sp.add_filter(BoomFilter())
        sp.use_hook(hook)
        with pytest.raises(ValueError, match="boom"):
            sp.run(Payload({"x": 0}))
        kinds = [e[0] for e in hook.events]
        assert "on_error" in kinds


# ── Timing observation ──────────────────────────────────────────────


class TestSyncPipelineObserve:
    """observe(timing=True) records step durations."""

    def test_timing_recorded(self):
        sp = Pipeline()
        sp.add_filter(AddOneFilter())
        sp.observe(timing=True)
        sp.run(Payload({"x": 0}))
        assert "AddOneFilter" in sp.state.timings
        assert sp.state.timings["AddOneFilter"] > 0


# ── Govern contracts ────────────────────────────────────────────────


# ── Performance ─────────────────────────────────────────────────────


class AsyncAddOne:

    async def call(self, payload):
        return payload.insert('x', payload.get('x') + 1)


class TestSyncPipelinePerformance:
    """Pipeline should be faster than Pipeline for tight loops."""

    def test_faster_than_async_pipeline(self):
        import asyncio
        from codeupipe import Pipeline

        # Async pipeline with same filter

        # Build both pipelines
        sp = Pipeline()
        sp.add_filter(AddOneFilter())

        ap = Pipeline()
        ap.add_filter(AsyncAddOne())

        p = Payload({"x": 0})

        # Warm up
        sp.run(p)
        asyncio.run(ap.run_async(p))

        n = 200
        t0 = time.monotonic()
        for _ in range(n):
            sp.run(p)
        sync_total = time.monotonic() - t0

        t0 = time.monotonic()
        for _ in range(n):
            asyncio.run(ap.run_async(p))
        async_total = time.monotonic() - t0

        sync_us = (sync_total / n) * 1_000_000
        async_us = (async_total / n) * 1_000_000
        print(f"\n  Pipeline={sync_us:.0f}us  Pipeline={async_us:.0f}us  "
              f"speedup={async_us/sync_us:.1f}x")

        # Pipeline should be at least 2x faster
        assert sync_total < async_total


# ── With PersistentSubprocess ───────────────────────────────────────


class TestTapFailureIsolation:
    """Plane B: a Tap failure never halts Plane A — same contract as Pipeline:
    recorded in state.errors, Tap counted as executed, no
    on_error hook, BaseExceptions still propagate."""

    class _Score:
        def call(self, payload):
            return payload.insert("score", 2)

    class _Boom:
        def observe(self, payload):
            raise ConnectionError("audit sink disconnected")

    class _ErrorHook(Hook):
        def __init__(self):
            self.errors = []

        def on_error(self, filter, error, payload):
            self.errors.append(error)

    @pytest.mark.unit
    @pytest.mark.core
    def test_run_contains_a_tap_failure(self):
        hook = self._ErrorHook()
        p = Pipeline()
        p.add_filter(self._Score())
        p.add_tap(self._Boom())
        p.use_hook(hook)

        result = p.run(Payload({}))

        assert result.get("score") == 2
        assert p.state.errors[-1][0] == "_Boom"
        assert "_Boom" in p.state.executed
        assert hook.errors == []

