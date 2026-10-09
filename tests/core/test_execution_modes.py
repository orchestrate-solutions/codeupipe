"""Tests for Ring 3 — Execution Modes.

Feature 1: run_sync() — synchronous wrapper so users don't need asyncio.run()
Feature 2: Parallel fan-out/fan-in — concurrent independent filters
Feature 3: Pipeline-as-step — nest a Pipeline inside another Pipeline
Feature 4: Pipeline-level retry/circuit-breaker
"""

import asyncio

import pytest

from codeupipe import Payload, Pipeline, Hook


class _ValuePositive:

    def test(self, payload):
        return payload.get('value', 0) > 0


class SubPipeline(Pipeline):
    """A named pipeline type, so it can be nested (conformance/API.md, step identity)."""


# ── Helpers ──────────────────────────────────────────────────

class AddTenFilter:
    def call(self, payload: Payload) -> Payload:
        return payload.insert("value", payload.get("value", 0) + 10)


class MultiplyFilter:
    def call(self, payload: Payload) -> Payload:
        return payload.insert("value", payload.get("value", 0) * 2)


class AppendTagFilter:
    """Appends a tag to a list to prove execution order."""
    def __init__(self, tag: str):
        self.tag = tag

    def call(self, payload: Payload) -> Payload:
        tags = list(payload.get("tags", []))
        tags.append(self.tag)
        return payload.insert("tags", tags)


class SlowFilter:
    """Simulates IO work — takes 0.1s."""
    def __init__(self, key: str, value):
        self.key = key
        self.value = value

    async def call(self, payload: Payload) -> Payload:
        await asyncio.sleep(0.1)
        return payload.insert(self.key, self.value)


class FailOnceFilter:
    """Fails N times then succeeds."""
    def __init__(self, fail_count: int = 1):
        self.fail_count = fail_count
        self.attempts = 0

    def call(self, payload: Payload) -> Payload:
        self.attempts += 1
        if self.attempts <= self.fail_count:
            raise RuntimeError(f"Fail #{self.attempts}")
        return payload.insert("recovered", True)


class AlwaysFailFilter:
    def call(self, payload: Payload) -> Payload:
        raise RuntimeError("permanent failure")


class CountingTap:
    def __init__(self):
        self.count = 0

    def observe(self, payload: Payload) -> None:
        self.count += 1


# ═══════════════════════════════════════════════════════════════
# Feature 1: run_sync()
# ═══════════════════════════════════════════════════════════════

class TestRunSync:
    """Pipeline.run() — synchronous convenience wrapper."""

    def test_run_sync_basic(self):
        """run_sync executes the pipeline without manual asyncio.run()."""
        pipe = Pipeline()
        pipe.add_filter(AddTenFilter())
        result = pipe.run(Payload({"value": 5}))
        assert result.get("value") == 15

    def test_run_sync_multi_step(self):
        pipe = Pipeline()
        pipe.add_filter(AddTenFilter())
        pipe.add_filter(MultiplyFilter())
        result = pipe.run(Payload({"value": 5}))
        assert result.get("value") == 30  # (5 + 10) * 2

    def test_run_sync_with_taps(self):
        tap = CountingTap()
        pipe = Pipeline()
        pipe.add_filter(AddTenFilter())
        pipe.add_tap(tap)
        result = pipe.run(Payload({"value": 1}))
        assert result.get("value") == 11
        assert tap.count == 1

    def test_run_sync_propagates_errors(self):
        pipe = Pipeline()
        pipe.add_filter(AlwaysFailFilter())
        with pytest.raises(RuntimeError, match="permanent failure"):
            pipe.run(Payload({}))

    def test_run_sync_updates_state(self):
        pipe = Pipeline()
        pipe.add_filter(AddTenFilter())
        result = pipe.run(Payload({"value": 0}))
        assert f"{__name__}.AddTenFilter" in pipe.state.executed


# ═══════════════════════════════════════════════════════════════
# Feature 2: Parallel fan-out / fan-in
# ═══════════════════════════════════════════════════════════════

class Set:

    def __init__(self, key, value):
        self.key, self.value = (key, value)

    def call(self, payload):
        return payload.insert(self.key, self.value)


# ═══════════════════════════════════════════════════════════════
# Feature 3: Pipeline-as-step (nesting)
# ═══════════════════════════════════════════════════════════════

class TestPipelineAsStep:
    """Nest a Pipeline inside another Pipeline as a regular step."""

    @pytest.mark.asyncio
    async def test_nested_pipeline_basic(self):
        """An inner pipeline runs as a single step in the outer pipeline."""
        inner = SubPipeline()
        inner.add_filter(AddTenFilter())
        inner.add_filter(MultiplyFilter())

        outer = Pipeline()
        outer.add_pipeline(inner)

        result = await outer.run_async(Payload({"value": 5}))
        assert result.get("value") == 30  # (5+10)*2

    @pytest.mark.asyncio
    async def test_nested_pipeline_with_surrounding_steps(self):
        """Steps before and after the nested pipeline all execute."""
        inner = SubPipeline()
        inner.add_filter(MultiplyFilter())

        outer = Pipeline()
        outer.add_filter(AddTenFilter())
        outer.add_pipeline(inner)
        outer.add_filter(AddTenFilter())

        result = await outer.run_async(Payload({"value": 5}))
        # 5 +10 = 15, *2 = 30, +10 = 40
        assert result.get("value") == 40

    @pytest.mark.asyncio
    async def test_nested_pipeline_state_tracked(self):
        """The nested pipeline step appears in outer pipeline state."""
        inner = SubPipeline()
        inner.add_filter(AddTenFilter())

        outer = Pipeline()
        outer.add_pipeline(inner)
        await outer.run_async(Payload({"value": 0}))

        assert f"{__name__}.SubPipeline" in outer.state.executed

    @pytest.mark.asyncio
    async def test_nested_pipeline_error_propagates(self):
        """Errors inside the nested pipeline propagate to the outer pipeline."""
        inner = SubPipeline()
        inner.add_filter(AlwaysFailFilter())

        outer = Pipeline()
        outer.add_filter(AddTenFilter())
        outer.add_pipeline(inner)

        with pytest.raises(RuntimeError, match="permanent failure"):
            await outer.run_async(Payload({"value": 0}))

    @pytest.mark.asyncio
    async def test_deeply_nested_pipelines(self):
        """Pipelines can nest multiple levels deep."""
        innermost = SubPipeline()
        innermost.add_filter(AddTenFilter())

        mid = SubPipeline()
        mid.add_pipeline(innermost)
        mid.add_filter(MultiplyFilter())

        outer = Pipeline()
        outer.add_pipeline(mid)

        result = await outer.run_async(Payload({"value": 5}))
        assert result.get("value") == 30  # (5+10)*2


    def test_nested_pipeline_run_sync(self):
        """Nested pipelines work through run_sync."""
        inner = SubPipeline()
        inner.add_filter(AddTenFilter())

        outer = Pipeline()
        outer.add_pipeline(inner)

        result = outer.run(Payload({"value": 5}))
        assert result.get("value") == 15


# ═══════════════════════════════════════════════════════════════
# Feature 4: Pipeline-level retry / circuit breaker
# ═══════════════════════════════════════════════════════════════

class ErrorCounter(Hook):

    def __init__(self):
        self.error_count = 0

    async def before(self, filter, payload):
        pass

    async def after(self, filter, payload):
        pass

    async def on_error(self, filter, error, payload):
        if filter is not None:
            self.error_count += 1


