"""Tests for Ring 3 — Execution Modes.

Feature 1: run_sync() — synchronous wrapper so users don't need asyncio.run()
Feature 2: Parallel fan-out/fan-in — concurrent independent filters
Feature 3: Pipeline-as-step — nest a Pipeline inside another Pipeline
Feature 4: Pipeline-level retry/circuit-breaker
"""

import asyncio

import pytest

from codeupipe import Payload, Pipeline, Valve, Hook


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


class TestParallelGroup:
    """Pipeline.add_parallel() — concurrent execution of independent filters."""

    @pytest.mark.asyncio
    async def test_parallel_basic(self):
        """Multiple filters run concurrently, results merged into payload."""
        pipe = Pipeline()
        pipe.add_parallel([
            SlowFilter("a", 1),
            SlowFilter("b", 2),
            SlowFilter("c", 3),
        ])

        result = await pipe.run_async(Payload({}))
        assert result.get("a") == 1
        assert result.get("b") == 2
        assert result.get("c") == 3

    @pytest.mark.asyncio
    async def test_parallel_is_faster_than_sequential(self):
        """3 × 0.1s filters in parallel should take ~0.1s, not ~0.3s."""
        pipe = Pipeline()
        pipe.add_parallel([
            SlowFilter("x", 1),
            SlowFilter("y", 2),
            SlowFilter("z", 3),
        ])

        import time
        start = time.monotonic()
        await pipe.run_async(Payload({}))
        elapsed = time.monotonic() - start

        assert elapsed < 0.25, f"Parallel took {elapsed:.2f}s — should be ~0.1s"

    @pytest.mark.asyncio
    async def test_parallel_preserves_existing_keys(self):
        """Pre-existing payload keys survive the parallel merge."""
        pipe = Pipeline()
        pipe.add_parallel([SlowFilter("new_key", 42)])

        result = await pipe.run_async(Payload({"existing": "kept"}))
        assert result.get("existing") == "kept"
        assert result.get("new_key") == 42

    @pytest.mark.asyncio
    async def test_parallel_state_tracked(self):
        """Parallel group appears in pipeline state."""
        pipe = Pipeline()
        pipe.add_parallel([SlowFilter("a", 1)])
        await pipe.run_async(Payload({}))
        assert f"parallel[{__name__}.SlowFilter]" in pipe.state.executed

    @pytest.mark.asyncio
    async def test_parallel_error_propagates(self):
        """If any filter in the parallel group fails, the error propagates."""
        pipe = Pipeline()
        pipe.add_parallel([
            SlowFilter("ok", 1),
            AlwaysFailFilter(),
        ])

        with pytest.raises(RuntimeError, match="permanent failure"):
            await pipe.run_async(Payload({}))

    @pytest.mark.asyncio
    async def test_parallel_with_named_filters(self):
        """Filters in a parallel group can be given individual names."""
        pipe = Pipeline()
        pipe.add_parallel([SlowFilter("a", 1), SlowFilter("b", 2)])
        result = await pipe.run_async(Payload({}))
        assert result.get("a") == 1
        assert result.get("b") == 2

    def test_parallel_of_async_filters_needs_run_async(self):
        """run() never starts an event loop: an async parallel member raises
        AsyncStepInSyncRun; run_async() runs it."""
        from codeupipe import AsyncStepInSyncRun

        pipe = Pipeline()
        pipe.add_parallel([SlowFilter("v", 99)])
        with pytest.raises(AsyncStepInSyncRun):
            pipe.run(Payload({}))
        assert asyncio.run(pipe.run_async(Payload({}))).get("v") == 99

    def test_parallel_of_sync_filters_runs_with_run(self):

        pipe = Pipeline()
        pipe.add_parallel([Set("a", 1), Set("b", 2)])
        assert pipe.run(Payload({})).to_dict() == {"a": 1, "b": 2}

    @pytest.mark.asyncio
    async def test_parallel_mixed_with_sequential(self):
        """Parallel step between sequential steps."""
        pipe = Pipeline()
        pipe.add_filter(AddTenFilter())
        pipe.add_parallel([
            SlowFilter("branch_a", "done"),
            SlowFilter("branch_b", "done"),
        ])
        pipe.add_filter(MultiplyFilter())

        result = await pipe.run_async(Payload({"value": 5}))
        assert result.get("value") == 30  # (5+10)*2
        assert result.get("branch_a") == "done"
        assert result.get("branch_b") == "done"


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

    @pytest.mark.asyncio
    async def test_nested_pipeline_with_valve(self):
        """A Valve can gate a nested pipeline."""
        inner = SubPipeline()
        inner.add_filter(MultiplyFilter())

        outer = Pipeline()
        valve = Valve(inner=inner, predicate=_ValuePositive())
        outer.add_filter(valve)

        # Positive: valve passes, inner runs
        result = await outer.run_async(Payload({"value": 5}))
        assert result.get("value") == 10

        # Zero: valve skips, payload unchanged
        result = await outer.run_async(Payload({"value": 0}))
        assert result.get("value") == 0

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


class TestPipelineRetry:
    """Pipeline.with_retry() — wraps entire pipeline execution with retry logic."""

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_transient_failure(self):
        """Pipeline retries on failure and eventually succeeds."""
        fail_filter = FailOnceFilter(fail_count=2)

        pipe = Pipeline()
        pipe.add_filter(fail_filter)

        retrying = pipe.with_retry(max_retries=3)
        result = await retrying.run_async(Payload({}))
        assert result.get("recovered") is True
        assert fail_filter.attempts == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises(self):
        """After max retries, the final error propagates."""
        pipe = Pipeline()
        pipe.add_filter(AlwaysFailFilter())

        retrying = pipe.with_retry(max_retries=3)
        with pytest.raises(RuntimeError, match="permanent failure"):
            await retrying.run_async(Payload({}))

    @pytest.mark.asyncio
    async def test_retry_zero_means_no_retry(self):
        """max_retries=0 means run once, no retry on failure."""
        pipe = Pipeline()
        pipe.add_filter(AlwaysFailFilter())

        retrying = pipe.with_retry(max_retries=0)
        with pytest.raises(RuntimeError):
            await retrying.run_async(Payload({}))

    def test_retry_run_sync(self):
        """with_retry works through run_sync."""
        fail_filter = FailOnceFilter(fail_count=1)
        pipe = Pipeline()
        pipe.add_filter(fail_filter)

        retrying = pipe.with_retry(max_retries=2)
        result = retrying.run(Payload({}))
        assert result.get("recovered") is True

    @pytest.mark.asyncio
    async def test_retry_preserves_hooks(self):
        """Hooks fire on each retry attempt."""


        counter = ErrorCounter()
        pipe = Pipeline()
        pipe.add_filter(FailOnceFilter(fail_count=2))
        pipe.use_hook(counter)

        retrying = pipe.with_retry(max_retries=3)
        result = await retrying.run_async(Payload({}))
        assert result.get("recovered") is True
        # on_error fires for each failed attempt
        assert counter.error_count == 2

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_threshold(self):
        """Circuit breaker opens after N consecutive failures."""
        from codeupipe.core.pipeline import CircuitOpenError

        pipe = Pipeline()
        pipe.add_filter(AlwaysFailFilter())

        breaker = pipe.with_circuit_breaker(failure_threshold=3)

        # Trip the circuit
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await breaker.run_async(Payload({}))

        # Circuit is now open — should fail fast without executing
        with pytest.raises(CircuitOpenError):
            await breaker.run_async(Payload({}))

    @pytest.mark.asyncio
    async def test_circuit_breaker_resets_on_success(self):
        """Success resets the failure counter."""
        fail_filter = FailOnceFilter(fail_count=2)
        pipe = Pipeline()
        pipe.add_filter(fail_filter)

        breaker = pipe.with_circuit_breaker(failure_threshold=5)

        # 2 failures
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await breaker.run_async(Payload({}))

        # 3rd attempt succeeds, resets counter
        result = await breaker.run_async(Payload({}))
        assert result.get("recovered") is True

    def test_circuit_breaker_run_sync(self):
        """Circuit breaker works through run_sync."""
        from codeupipe.core.pipeline import CircuitOpenError

        pipe = Pipeline()
        pipe.add_filter(AlwaysFailFilter())
        breaker = pipe.with_circuit_breaker(failure_threshold=2)

        for _ in range(2):
            with pytest.raises(RuntimeError):
                breaker.run(Payload({}))

        with pytest.raises(CircuitOpenError):
            breaker.run(Payload({}))
