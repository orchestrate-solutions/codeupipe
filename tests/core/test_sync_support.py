"""
Tests confirming that sync (non-async) filters, taps, hooks, and valve
inner-filters all work correctly alongside their async equivalents.
"""

import asyncio

import pytest
from codeupipe import Payload, Pipeline, Valve, Hook

# ---------------------------------------------------------------------------

def run(coro):
    return asyncio.run(coro)


# ===========================================================================
# Sync Filters
# ===========================================================================

class SyncDouble:

    def call(self, payload: Payload) -> Payload:
        return payload.insert('value', payload.get('value', 0) * 2)

class SyncAdd:

    def call(self, payload: Payload) -> Payload:
        return payload.insert('n', payload.get('n', 0) + 1)

class AsyncMul:

    async def call(self, payload: Payload) -> Payload:
        return payload.insert('n', payload.get('n', 0) * 3)

class SyncPass:

    def call(self, payload: Payload) -> Payload:
        return payload


class TestSyncFilter:
    def test_sync_filter_executes(self):

        async def go():
            pipeline = Pipeline()
            pipeline.add_filter(SyncDouble())
            return await pipeline.run_async(Payload({"value": 5}))

        assert run(go()).get("value") == 10

    def test_sync_and_async_filters_interleaved(self):


        async def go():
            pipeline = Pipeline()
            pipeline.add_filter(SyncAdd())   # sync
            pipeline.add_filter(AsyncMul())   # async
            pipeline.add_filter(SyncAdd())  # sync again
            return await pipeline.run_async(Payload({"n": 0}))

        # (0+1)*3 + 1 = 4
        assert run(go()).get("n") == 4

    def test_sync_filter_recorded_in_state(self):

        async def go():
            pipeline = Pipeline()
            pipeline.add_filter(SyncPass())
            await pipeline.run_async(Payload({}))
            return pipeline.state

        state = run(go())
        assert f"{__name__}.SyncPass" in state.executed


# ===========================================================================
# Sync Taps
# ===========================================================================

class SyncNopTap:

    def observe(self, payload: Payload) -> None:
        pass


class SyncSeenTap:
    def __init__(self):
        self.seen = []

    def observe(self, payload: Payload) -> None:    # no async
        self.seen.append(payload.get("x"))


class AsyncSeenTap:
    def __init__(self):
        self.seen = []

    async def observe(self, payload: Payload) -> None:
        self.seen.append(payload.get("x"))


class _IsVip:

    def test(self, payload):
        return payload.get('vip') is True


class TestSyncTap:
    def test_sync_tap_observes_without_modifying(self):
        tap = SyncSeenTap()

        async def go():
            pipeline = Pipeline()
            pipeline.add_tap(tap)
            return await pipeline.run_async(Payload({"x": 42}))

        result = run(go())
        assert result.get("x") == 42
        assert tap.seen == [42]

    def test_sync_tap_recorded_in_state(self):

        async def go():
            pipeline = Pipeline()
            pipeline.add_tap(SyncNopTap())
            await pipeline.run_async(Payload({}))
            return pipeline.state

        state = run(go())
        assert f"{__name__}.SyncNopTap" in state.executed


# ===========================================================================
# Sync Hooks
# ===========================================================================

class PassFilter:

    async def call(self, payload: Payload) -> Payload:
        return payload

class BoomFilter:

    async def call(self, payload: Payload) -> Payload:
        raise RuntimeError('boom')


class TestSyncHook:
    def test_sync_hook_methods_called(self):
        log = []

        class SyncHook(Hook):
            def before(self, step, payload: Payload) -> None:   # no async
                log.append(f"before:{step or 'pipeline'}")

            def after(self, step, payload: Payload) -> None:    # no async
                log.append(f"after:{step or 'pipeline'}")


        async def go():
            pipeline = Pipeline()
            pipeline.use_hook(SyncHook())
            pipeline.add_filter(PassFilter())
            await pipeline.run_async(Payload({}))

        run(go())
        assert log == [
            "before:pipeline",
            f"before:{__name__}.PassFilter",
            f"after:{__name__}.PassFilter",
            "after:pipeline",
        ]

    def test_sync_on_error_hook_called_on_failure(self):
        errors = []

        class SyncErrHook(Hook):
            def on_error(self, filter, error: Exception, payload: Payload) -> None:
                where = "pipeline" if filter is None else filter
                errors.append(f"{where}:{error}")


        async def go():
            pipeline = Pipeline()
            pipeline.use_hook(SyncErrHook())
            pipeline.add_filter(BoomFilter())
            try:
                await pipeline.run_async(Payload({}))
            except RuntimeError:
                pass

        run(go())
        # the failing step first, then the pipeline
        assert errors == [f"{__name__}.BoomFilter:boom", "pipeline:boom"]


# ===========================================================================
# Sync Valve inner filter
# ===========================================================================

class SyncDiscount:

    def call(self, payload: Payload) -> Payload:
        return payload.insert('total', payload.get('total', 0) * 0.9)

class SyncDiscount2:

    def call(self, payload: Payload) -> Payload:
        return payload.insert('total', payload.get('total', 0) * 0.9)


class TestSyncValveInner:
    def test_sync_inner_filter_executes_when_predicate_true(self):

        valve = Valve(inner=SyncDiscount(), predicate=_IsVip())

        async def go():
            pipeline = Pipeline()
            pipeline.add_filter(valve)
            return await pipeline.run_async(Payload({"vip": True, "total": 200}))

        result = run(go())
        assert result.get("total") == 180.0

    def test_sync_inner_filter_skipped_when_predicate_false(self):

        valve = Valve(inner=SyncDiscount2(), predicate=_IsVip())

        async def go():
            pipeline = Pipeline()
            pipeline.add_filter(valve)
            await pipeline.run_async(Payload({"vip": False, "total": 200}))
            return pipeline.state

        state = run(go())
        assert f"{__name__}.SyncDiscount2" in state.skipped


# ===========================================================================
# Explicit async registration
# ===========================================================================

class AsyncMul2:

    async def call(self, payload: Payload) -> Payload:
        return payload.insert('n', payload.get('n', 0) * 3)

class AsyncPass:

    async def call(self, payload: Payload) -> Payload:
        return payload

class AsyncTapper:

    async def observe(self, payload: Payload) -> None:
        pass


class TestDeclaredAsync:
    def test_explicit_async_filter_executes(self):

        async def go():
            pipeline = Pipeline()
            pipeline.add_async_filter(AsyncMul2())
            return await pipeline.run_async(Payload({"n": 2}))

        assert run(go()).get("n") == 6

    def test_explicit_async_tap_executes(self):
        tap = AsyncSeenTap()

        async def go():
            pipeline = Pipeline()
            pipeline.add_async_tap(tap)
            return await pipeline.run_async(Payload({"x": 42}))

        result = run(go())
        assert result.get("x") == 42
        assert tap.seen == [42]

    def test_describe_marks_explicit_async_steps(self):


        pipeline = Pipeline()
        pipeline.add_async_filter(AsyncPass())
        pipeline.add_async_tap(AsyncTapper())

        steps = pipeline.describe()["steps"]
        assert steps[0]["type"] == "async_filter"
        assert steps[1]["type"] == "async_tap"


# ===========================================================================
# Pipeline.run_sync fast path
# ===========================================================================

class SyncAdd2:

    def call(self, payload: Payload) -> Payload:
        return payload.insert('n', payload.get('n', 0) + 1)

class AsyncAdd:

    async def call(self, payload: Payload) -> Payload:
        return payload.insert('n', payload.get('n', 0) + 1)


class TestPipelineRunSyncFastPath:
    def test_run_sync_works_inside_running_loop_for_sync_only_pipeline(self):

        async def go():
            pipeline = Pipeline()
            pipeline.add_filter(SyncAdd2())
            return pipeline.run(Payload({"n": 1}))

        assert run(go()).get("n") == 2

    def test_an_explicit_async_pipeline_needs_run_async(self):
        from codeupipe import AsyncStepInSyncRun


        pipeline = Pipeline()
        pipeline.add_async_filter(AsyncAdd())
        with pytest.raises(AsyncStepInSyncRun):
            pipeline.run(Payload({"n": 1}))
        assert asyncio.run(pipeline.run_async(Payload({"n": 1}))).get("n") == 2
