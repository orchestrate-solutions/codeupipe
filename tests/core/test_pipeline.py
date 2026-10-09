"""
Tests for Pipeline

Testing the Pipeline orchestrator with filters, valves, taps, and hooks.
"""

import pytest
import asyncio
from typing import Optional
from codeupipe.core.payload import Payload
from codeupipe.core.filter import Filter
from codeupipe.core.pipeline import Pipeline
from codeupipe.core.valve import Valve
from codeupipe.core.hook import Hook


class LoggingHook(Hook):
    """Simple hook for testing that logs execution."""

    def __init__(self):
        super().__init__()
        self.log = []

    async def before(self, step: Optional[str], payload: Payload) -> None:
        # hooks receive the step's identity (API contract), None for the pipeline
        self.log.append(f"before_{step if step is not None else 'pipeline_start'}")

    async def after(self, step: Optional[str], payload: Payload) -> None:
        # hooks receive the step's identity (API contract), None for the pipeline
        self.log.append(f"after_{step if step is not None else 'pipeline_end'}")

    async def on_error(self, step: Optional[str], error: Exception, payload: Payload) -> None:
        self.log.append(f"error_{step if step is not None else 'pipeline'}_{str(error)}")


class TestFilter:

    async def call(self, payload):
        return payload.insert('processed', True)

class Filter1:

    async def call(self, payload):
        return payload.insert('step1', True)

class Filter2:

    async def call(self, payload):
        return payload.insert('step2', True)

class TestFilter2:

    async def call(self, payload):
        return payload.insert('done', True)


class TestSimplePipeline:
    """Test the Pipeline."""

    @pytest.mark.unit
    @pytest.mark.core
    def test_empty_pipeline(self):
        """Test running an empty pipeline."""
        pipeline = Pipeline()

        async def run_test():
            payload = Payload({"input": "test"})
            result = await pipeline.run_async(payload)
            assert result.get("input") == "test"

        asyncio.run(run_test())

    @pytest.mark.unit
    @pytest.mark.core
    def test_single_filter_pipeline(self):
        """Test pipeline with a single filter."""
        pipeline = Pipeline()


        pipeline.add_filter(TestFilter())

        async def run_test():
            payload = Payload({"input": "test"})
            result = await pipeline.run_async(payload)

            assert result.get("processed") is True
            assert result.get("input") == "test"

        asyncio.run(run_test())

    @pytest.mark.unit
    @pytest.mark.core
    def test_multiple_filters_pipeline(self):
        """Test pipeline with multiple filters."""
        pipeline = Pipeline()


        pipeline.add_filter(Filter1())
        pipeline.add_filter(Filter2())

        async def run_test():
            result = await pipeline.run_async(Payload())
            assert result.get("step1") is True
            assert result.get("step2") is True

        asyncio.run(run_test())

    @pytest.mark.unit
    @pytest.mark.core
    def test_pipeline_state_tracking(self):
        """Test that pipeline tracks execution state."""
        pipeline = Pipeline()


        pipeline.add_filter(TestFilter2())
        pipeline.add_filter(TestFilter2())

        async def run_test():
            await pipeline.run_async(Payload())
            assert pipeline.state.executed == [f"{__name__}.TestFilter2", f"{__name__}.TestFilter2#2"]

        asyncio.run(run_test())


class SetValueFilter:

    async def call(self, payload):
        return payload.insert('value', 42)

class GatedFilter:

    async def call(self, payload):
        return payload.insert('gated_ran', True)

class SuccessFilter:

    async def call(self, payload):
        return payload.insert('success', True)

class FailureFilter:

    async def call(self, payload):
        return payload.insert('failure', True)

class _Predicate:

    def test(self, p):
        return p.get('value') == 42

class _Predicate2:

    def test(self, p):
        return False

class _Predicate3:

    def test(self, p):
        return p.get('success') is True

class _Predicate4:

    def test(self, p):
        return p.get('success') is not True


class MarkFirst:
    async def call(self, payload):
        return payload.insert("first_ran", True)


class MarkGated:
    async def call(self, payload):
        return payload.insert("gated_ran", True)


class _Always:

    def test(self, payload):
        return True


class _Never:

    def test(self, payload):
        return False


class ObserverTap:
    def __init__(self):
        self.values = []

    async def observe(self, payload):
        self.values.append(payload.get("value"))


class TestValveInPipeline:
    """Test Valves providing conditional execution in pipelines."""

    @pytest.mark.unit
    @pytest.mark.core
    def test_valve_allows_when_predicate_true(self):
        """Test that a Valve executes its filter when predicate is True."""
        pipeline = Pipeline()


        pipeline.add_filter(SetValueFilter())
        pipeline.add_filter(Valve(GatedFilter(), _Predicate()))

        async def run_test():
            result = await pipeline.run_async(Payload())
            assert result.get("gated_ran") is True

        asyncio.run(run_test())

    @pytest.mark.unit
    @pytest.mark.core
    def test_valve_blocks_when_predicate_false(self):
        """Test that a Valve skips its filter when predicate is False."""
        pipeline = Pipeline()
        pipeline.add_filter(MarkFirst())
        pipeline.add_filter(Valve(MarkGated(), _Predicate2()))

        async def run_test():
            result = await pipeline.run_async(Payload())
            assert pipeline.state.executed == [f"{__name__}.MarkFirst"]
            assert pipeline.state.skipped == [f"{__name__}.MarkGated"]
            assert result.get("first_ran") is True
            assert result.get("gated_ran") is None

        asyncio.run(run_test())

    @pytest.mark.unit
    @pytest.mark.core
    def test_valve_conditional_branching(self):
        """Test conditional execution — success path runs, failure path skipped."""
        pipeline = Pipeline()


        pipeline.add_filter(SuccessFilter())
        pipeline.add_filter(Valve(SuccessFilter(), _Predicate3()))
        pipeline.add_filter(Valve(FailureFilter(), _Predicate4()))

        async def run_test():
            result = await pipeline.run_async(Payload())
            assert result.get("success") is True
            assert result.get("failure") is None

        asyncio.run(run_test())


class SetFilter:

    async def call(self, payload):
        return payload.insert('value', 42)

class NoopTap:

    async def observe(self, payload):
        pass


class TestTapInPipeline:
    """Test Taps providing observation in pipelines."""

    @pytest.mark.unit
    @pytest.mark.core
    def test_tap_observes_without_modifying(self):
        """Test that a Tap observes payload without modifying it."""
        pipeline = Pipeline()
        observer = ObserverTap()
        pipeline.add_filter(SetFilter())
        pipeline.add_tap(observer)

        async def run_test():
            result = await pipeline.run_async(Payload())
            assert result.get("value") == 42
            assert observer.values == [42]

        asyncio.run(run_test())

    @pytest.mark.unit
    @pytest.mark.core
    def test_tap_tracked_in_state(self):
        """Test that taps are tracked in pipeline state."""
        pipeline = Pipeline()


        pipeline.add_tap(NoopTap())

        async def run_test():
            await pipeline.run_async(Payload())
            assert f"{__name__}.NoopTap" in pipeline.state.executed

        asyncio.run(run_test())


class NamedFilter3:

    def __init__(self, name):
        self.name = name

    async def call(self, payload):
        return payload

class FailingFilter:

    async def call(self, payload):
        raise ValueError('Test error')


class TestPipelineWithHook:
    """Test pipelines with hooks."""

    @pytest.mark.unit
    @pytest.mark.core
    def test_hook_execution(self):
        """Test that hooks are called."""
        pipeline = Pipeline()
        hook = LoggingHook()


        pipeline.use_hook(hook)
        pipeline.add_filter(NamedFilter3("test_filter"))

        async def run_test():
            await pipeline.run_async(Payload())

            assert "before_pipeline_start" in hook.log
            # hooks receive the step's identity (API contract)
            assert f"before_{__name__}.NamedFilter3" in hook.log
            assert f"after_{__name__}.NamedFilter3" in hook.log
            assert "after_pipeline_end" in hook.log

        asyncio.run(run_test())

    @pytest.mark.unit
    @pytest.mark.core
    def test_hook_error_handling(self):
        """Test hook error handling."""
        pipeline = Pipeline()
        hook = LoggingHook()


        pipeline.use_hook(hook)
        pipeline.add_filter(FailingFilter())

        async def run_test():
            with pytest.raises(ValueError):
                await pipeline.run_async(Payload())

            assert any("error" in entry for entry in hook.log)

        asyncio.run(run_test())


class ValidationFilter:

    async def call(self, payload):
        data = payload.get('data')
        if not data:
            raise ValueError('No data provided')
        return payload.insert('validated', True)

class ProcessingFilter:

    async def call(self, payload):
        data = payload.get('data')
        processed = f'processed_{data}'
        return payload.insert('result', processed)


class TestPipelineIntegration:
    """Integration tests for pipeline functionality."""

    @pytest.mark.integration
    @pytest.mark.core
    def test_complete_workflow(self):
        """Test a complete workflow with validation, processing, and hooks."""
        pipeline = Pipeline()
        hook = LoggingHook()


        pipeline.use_hook(hook)
        pipeline.add_filter(ValidationFilter())
        pipeline.add_filter(ProcessingFilter())

        async def run_test():
            payload = Payload({"data": "test_input"})
            result = await pipeline.run_async(payload)

            assert result.get("validated") is True
            assert result.get("result") == "processed_test_input"
            assert result.get("data") == "test_input"

        asyncio.run(run_test())


class TestRunSyncWithValves:
    """``Pipeline.run_sync`` keeps a Valve over a sync filter on the sync path.

    ``Valve.call`` is async (its inner *may* be), so ``add_filter`` classifies
    every Valve as ``async_filter`` and ``run_sync`` used to fall back to
    ``asyncio.run`` for the whole pipeline: ~150 µs vs ~6 µs per run, and a
    RuntimeError inside a running event loop. Pipeline already fixed this
    via ``Valve.call_sync``; Pipeline had not.
    """

    class _Mark:
        def call(self, payload):
            return payload.insert("marked", True)

    class _AsyncMark:
        async def call(self, payload):
            return payload.insert("marked", True)

    def _pipeline(self, inner, predicate):
        p = Pipeline()
        p.add_filter(Valve(inner, predicate))
        return p

    @pytest.mark.unit
    @pytest.mark.core
    def test_run_sync_with_a_sync_valve_works_inside_a_running_event_loop(self):
        p = self._pipeline(self._Mark(), _Always())

        async def caller():
            return p.run(Payload({}))

        assert asyncio.run(caller()).get("marked") is True

    @pytest.mark.unit
    @pytest.mark.core
    def test_run_sync_records_a_closed_valve_as_skipped(self):
        p = self._pipeline(self._Mark(), _Never())

        result = p.run(Payload({}))

        assert result.get("marked") is None
        assert p.state.skipped == [f"{__name__}.TestRunSyncWithValves._Mark"]
        assert p.state.executed == []

    @pytest.mark.unit
    @pytest.mark.core
    def test_a_valve_over_an_async_filter_needs_run_async(self):
        from codeupipe import AsyncStepInSyncRun

        p = self._pipeline(self._AsyncMark(), _Always())

        with pytest.raises(AsyncStepInSyncRun):
            p.run(Payload({}))
        result = asyncio.run(p.run_async(Payload({})))
        assert result.get("marked") is True
        assert p.state.executed == [f"{__name__}.TestRunSyncWithValves._AsyncMark"]


class _Predicate5:

    def test(self, payload):
        return True


class TestTapFailureIsolation:
    """Plane B: a Tap failure never halts Plane A.

    The Tap's ``Exception`` is recorded in
    ``state.errors`` under the Tap's name, the Tap still counts as executed,
    the payload continues unchanged, and ``on_error`` hooks do not fire —
    hooks govern Plane A. Non-``Exception`` errors (KeyboardInterrupt,
    SystemExit) still propagate.
    """

    class _Score:
        def call(self, payload):
            return payload.insert("score", 2)

    class _Boom:
        def observe(self, payload):
            raise ConnectionError("audit sink disconnected")

    class _AsyncBoom:
        async def observe(self, payload):
            raise ConnectionError("async sink disconnected")

    class _Interrupt:
        def observe(self, payload):
            raise KeyboardInterrupt

    class _ErrorHook(Hook):
        def __init__(self):
            self.errors = []

        def on_error(self, filter, error, payload):
            self.errors.append(error)

    def _pipeline(self, tap, hook=None):
        p = Pipeline()
        p.add_filter(self._Score())
        p.add_tap(tap)
        p.add_filter(Valve(self._Score(), _Predicate5()))
        if hook is not None:
            p.use_hook(hook)
        return p

    def _assert_contained(self, p, result):
        assert result.get("score") == 2
        tap = next(i for i in p.identities if i.endswith(("._Boom", "._AsyncBoom")))
        assert p.state.errors[-1][0] == tap
        assert isinstance(p.state.errors[-1][1], ConnectionError)
        assert tap in p.state.executed
        assert f"{__name__}.TestTapFailureIsolation._Score#2" in p.state.executed

    @pytest.mark.unit
    @pytest.mark.core
    def test_run_fast_path_contains_a_sync_tap_failure(self):
        p = self._pipeline(self._Boom())
        self._assert_contained(p, asyncio.run(p.run_async(Payload({}))))

    @pytest.mark.unit
    @pytest.mark.core
    def test_run_fast_path_contains_an_async_tap_failure(self):
        p = self._pipeline(self._AsyncBoom())
        self._assert_contained(p, asyncio.run(p.run_async(Payload({}))))

    @pytest.mark.unit
    @pytest.mark.core
    def test_run_with_hooks_contains_a_tap_failure_without_firing_on_error(self):
        hook = self._ErrorHook()
        p = self._pipeline(self._Boom(), hook)
        self._assert_contained(p, asyncio.run(p.run_async(Payload({}))))
        assert hook.errors == []

    @pytest.mark.unit
    @pytest.mark.core
    def test_run_with_hooks_contains_an_async_tap_failure(self):
        p = self._pipeline(self._AsyncBoom(), self._ErrorHook())
        self._assert_contained(p, asyncio.run(p.run_async(Payload({}))))

    @pytest.mark.unit
    @pytest.mark.core
    def test_run_sync_fast_path_contains_a_tap_failure(self):
        p = self._pipeline(self._Boom())
        self._assert_contained(p, p.run(Payload({})))


    @pytest.mark.unit
    @pytest.mark.core
    def test_base_exceptions_from_a_tap_still_propagate(self):
        p = self._pipeline(self._Interrupt())
        with pytest.raises(KeyboardInterrupt):
            p.run(Payload({}))
